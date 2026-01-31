from dataclasses import dataclass
from typing import Dict, List, Optional
from pyxcp import types
from pyxcp.master.errorhandler import wrapped

@dataclass
class Page:
    segment_number: int
    page_number: int
    properties: Optional[types.PageProperties] = None
    init_segment: int = 0

@dataclass
class Segment:
    number: int
    max_pages: int
    address_extension: int
    max_mapping: int
    compression_method: int
    encryption_method: int
    pages: Dict[int, Page]
    address: Optional[int] = None
    length: Optional[int] = None
    mode: int = 0  # Current segment mode (e.g., Freeze)

class Calibration:
    """Standardized Calibration API for page management.
    
    This class abstracts away the complexity of segments and pages,
    providing a higher-level interface for managing calibration data.
    """
    
    def __init__(self, master):
        self.master = master
        self.segments: Dict[int, Segment] = {}
        self.max_segments: int = 0
        self.freeze_supported: bool = False
        self._initialized: bool = False

    @wrapped
    def refresh(self):
        """Discovers the logical memory layout of the slave (segments and pages)."""
        pag_info = self.master.getPagProcessorInfo()
        self.max_segments = pag_info.maxSegments
        self.freeze_supported = pag_info.pagProperties.freezeSupported
        
        self.segments.clear()
        for i in range(self.max_segments):
            # Mode 1: get standard info for this segment
            seg_info = self.master.getSegmentInfo(mode=1, segment_number=i, segment_info=0, mapping_index=0)
            
            # Mode 0: get basic address info (address/length)
            # Some slaves might not support this or it might be optional
            try:
                addr_info = self.master.getSegmentInfo(mode=0, segment_number=i, segment_info=0, mapping_index=0)
                len_info = self.master.getSegmentInfo(mode=0, segment_number=i, segment_info=1, mapping_index=0)
                address = addr_info.basicInfo
                length = len_info.basicInfo
            except Exception:
                address = None
                length = None
            
            segment = Segment(
                number=i,
                max_pages=seg_info.maxPages,
                address_extension=seg_info.addressExtension,
                max_mapping=seg_info.maxMapping,
                compression_method=seg_info.compressionMethod,
                encryption_method=seg_info.encryptionMethod,
                pages={},
                address=address,
                length=length
            )
            
            for p in range(segment.max_pages):
                page_info, init_seg = self.master.getPageInfo(i, p)
                segment.pages[p] = Page(
                    segment_number=i,
                    page_number=p,
                    properties=page_info,
                    init_segment=init_seg
                )
            
            segment.mode = self.master.getSegmentMode(i) or 0
            self.segments[i] = segment
            
        self._initialized = True

    def _check_initialized(self):
        if not self._initialized:
            self.refresh()

    @wrapped
    def set_page(self, segment: int, page: int, mode: int):
        """Set active page for a segment.
        
        Parameters
        ----------
        segment : int
            Segment number.
        page : int
            Page number.
        mode : int
            Bitmask: 0x01 (ECU access), 0x02 (XCP access).
        """
        self._check_initialized()
        if segment not in self.segments:
            raise ValueError(f"Invalid segment number: {segment}")
        if page not in self.segments[segment].pages:
            raise ValueError(f"Invalid page number {page} for segment {segment}")
            
        self.master.setCalPage(mode, segment, page)

    @wrapped
    def set_all_segments_page(self, page: int, mode: int):
        """Set active page for all segments.
        
        Parameters
        ----------
        page : int
            Page number.
        mode : int
            Bitmask: 0x01 (ECU access), 0x02 (XCP access).
        """
        # XCP command SET_CAL_PAGE with bit 0x80 in mode means "all segments"
        self.master.setCalPage(mode | 0x80, 0, page)

    @wrapped
    def get_page(self, segment: int, mode: int) -> int:
        """Get current active page for a segment.
        
        Parameters
        ----------
        segment : int
            Segment number.
        mode : int
            0x01 for ECU access, 0x02 for XCP access.
        
        Returns
        -------
        int
            Page number.
        """
        return self.master.getCalPage(mode, segment)

    @wrapped
    def copy_page(self, src_segment: int, src_page: int, dst_segment: int, dst_page: int):
        """Copy data from one page to another."""
        self.master.copyCalPage(src_segment, src_page, dst_segment, dst_page)

    @wrapped
    def set_freeze_mode(self, segment: int, enabled: bool):
        """Enable or disable freeze mode for a segment."""
        self._check_initialized()
        if not self.freeze_supported:
            raise RuntimeError("Freeze mode not supported by slave.")
        
        mode = 1 if enabled else 0
        self.master.setSegmentMode(mode, segment)
        if segment in self.segments:
            self.segments[segment].mode = mode

    @wrapped
    def is_frozen(self, segment: int) -> bool:
        """Check if a segment is in freeze mode."""
        mode = self.master.getSegmentMode(segment)
        return bool(mode & 0x01)

    @wrapped
    def save_all(self):
        """Request the slave to save calibration data into non-volatile memory.
        
        For each segment in FREEZE mode, the slave saves the current active XCP page
        into the non-volatile memory (Page 0 of INIT_SEGMENT).
        """
        # SET_REQUEST: bit 0 is STORE_CAL_REQ
        self.master.setRequest(mode=0x01, session_configuration_id=0)

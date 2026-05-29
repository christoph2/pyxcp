from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from pyxcp.types import PagePropertiesInfo

# Constants for Page Management
CAL_PAGE_MODE_ECU = 0x01
CAL_PAGE_MODE_XCP = 0x02
CAL_PAGE_MODE_ALL = 0x80


@dataclass
class Page:
    segment_number: int
    page_number: int
    properties: Optional["PagePropertiesInfo"] = None
    init_segment: int = 0

    def __repr__(self):
        props = f", props={self.properties}" if self.properties else ""
        return f"Page(seg={self.segment_number}, pg={self.page_number}{props})"

    # ------------------------------------------------------------------
    # Access-control helpers (delegate to PagePropertiesInfo)
    # ------------------------------------------------------------------

    def can_xcp_write(self) -> bool:
        """True if the XCP master may write to this page at all."""
        return self.properties is not None and self.properties.xcp_write_access

    def can_xcp_read(self) -> bool:
        """True if the XCP master may read from this page at all."""
        return self.properties is not None and self.properties.xcp_read_access

    def can_ecu_access(self) -> bool:
        """True if the ECU may access this page at all."""
        return self.properties is not None and self.properties.ecu_access


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

    def __repr__(self):
        addr_str = f", addr=0x{self.address:08X}" if self.address is not None else ""
        return f"Segment(#{self.number}, pages={len(self.pages)}/{self.max_pages}{addr_str}, mode={self.mode})"


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

    def __repr__(self):
        return f"Calibration(segments={len(self.segments)}, freeze_supported={self.freeze_supported})"

    def refresh(self):
        """Discovers the logical memory layout of the slave (segments and pages)."""
        try:
            pag_info = self.master.getPagProcessorInfo()
            self.max_segments = pag_info.maxSegments
            self.freeze_supported = pag_info.pagProperties.freezeSupported
        except Exception as e:
            raise RuntimeError(f"Failed to get PAG processor info: {e}") from e

        self.segments.clear()
        for i in range(self.max_segments):
            try:
                seg_info = self.master.getSegmentInfo(mode=1, segment_number=i, segment_info=0, mapping_index=0)

                address = None
                length = None
                try:
                    addr_info = self.master.getSegmentInfo(mode=0, segment_number=i, segment_info=0, mapping_index=0)
                    address = addr_info.basicInfo
                    len_info = self.master.getSegmentInfo(mode=0, segment_number=i, segment_info=1, mapping_index=0)
                    length = len_info.basicInfo
                except Exception:
                    pass

                segment = Segment(
                    number=i,
                    max_pages=seg_info.maxPages,
                    address_extension=seg_info.addressExtension,
                    max_mapping=seg_info.maxMapping,
                    compression_method=seg_info.compressionMethod,
                    encryption_method=seg_info.encryptionMethod,
                    pages={},
                    address=address,
                    length=length,
                )

                for p in range(segment.max_pages):
                    try:
                        # getPageInfo() returns a PageInfo dataclass (not a tuple)
                        page_info = self.master.getPageInfo(i, p)
                        segment.pages[p] = Page(
                            segment_number=i,
                            page_number=p,
                            properties=page_info.properties,
                            init_segment=page_info.init_segment,
                        )
                    except Exception:
                        pass

                try:
                    segment.mode = self.master.getSegmentMode(i) or 0
                except Exception:
                    segment.mode = 0

                self.segments[i] = segment

            except Exception:
                # If we can't get basic segment info, skip this segment
                continue

        self._initialized = True

    def _check_initialized(self):
        if not self._initialized:
            self.refresh()

    def set_page(self, segment: int, page: int, mode: int = CAL_PAGE_MODE_ECU | CAL_PAGE_MODE_XCP):
        """Set active page for a segment.

        Parameters
        ----------
        segment : int
            Segment number.
        page : int
            Page number.
        mode : int, optional
            Bitmask: 0x01 (ECU access), 0x02 (XCP access).
            Defaults to both ECU and XCP access.

        Raises
        ------
        ValueError
            If the segment or page number is invalid.
        PermissionError
            If the page properties forbid the requested access mode.
        """
        self._check_initialized()
        if segment not in self.segments:
            raise ValueError(f"Invalid segment number: {segment}")
        if page not in self.segments[segment].pages:
            raise ValueError(f"Invalid page number {page} for segment {segment}")

        pg = self.segments[segment].pages[page]
        if pg.properties is not None:
            if (mode & CAL_PAGE_MODE_XCP) and not pg.can_xcp_write():
                raise PermissionError(
                    f"Page {page} of segment {segment} does not allow XCP write access "
                    f"(xcp_write_access_with_ecu={pg.properties.xcp_write_access_with_ecu}, "
                    f"xcp_write_access_without_ecu={pg.properties.xcp_write_access_without_ecu})."
                )
            if (mode & CAL_PAGE_MODE_ECU) and not pg.can_ecu_access():
                raise PermissionError(
                    f"Page {page} of segment {segment} does not allow ECU access "
                    f"(ecu_access_with_xcp={pg.properties.ecu_access_with_xcp}, "
                    f"ecu_access_without_xcp={pg.properties.ecu_access_without_xcp})."
                )

        self.master.setCalPage(mode, segment, page)

    def set_ecu_page(self, segment: int, page: int):
        """Convenience method to set the ECU page."""
        self.set_page(segment, page, CAL_PAGE_MODE_ECU)

    def set_xcp_page(self, segment: int, page: int):
        """Convenience method to set the XCP page."""
        self.set_page(segment, page, CAL_PAGE_MODE_XCP)

    def set_all_pages(self, page: int, mode: int = CAL_PAGE_MODE_ECU | CAL_PAGE_MODE_XCP):
        """Set active page for all segments.

        Parameters
        ----------
        page : int
            Page number.
        mode : int, optional
            Bitmask: 0x01 (ECU access), 0x02 (XCP access).
            Defaults to both ECU and XCP access.
        """
        # XCP command SET_CAL_PAGE with bit 0x80 in mode means "all segments"
        self.master.setCalPage(mode | CAL_PAGE_MODE_ALL, 0, page)

    def set_all_segments_page(self, page: int, mode: int):
        """Legacy alias for set_all_pages."""
        self.set_all_pages(page, mode)

    def get_page(self, segment: int, mode: int = CAL_PAGE_MODE_XCP) -> int:
        """Get current active page for a segment.

        Parameters
        ----------
        segment : int
            Segment number.
        mode : int, optional
            0x01 for ECU access, 0x02 for XCP access.
            Defaults to XCP access.

        Returns
        -------
        int
            Page number.
        """
        return self.master.getCalPage(mode, segment)

    def get_current_config(self) -> Dict[int, Dict[str, int]]:
        """Returns the current active pages for all discovered segments.

        Returns
        -------
        dict
            A dictionary mapping segment numbers to their active ECU and XCP pages.
        """
        self._check_initialized()
        config = {}
        for seg_idx in self.segments:
            try:
                ecu_page = self.get_page(seg_idx, CAL_PAGE_MODE_ECU)
                xcp_page = self.get_page(seg_idx, CAL_PAGE_MODE_XCP)
                config[seg_idx] = {"ecu_page": ecu_page, "xcp_page": xcp_page}
            except Exception:
                # If a segment cannot be queried, skip it in the config report
                pass
        return config

    def copy_page(self, src_segment: int, src_page: int, dst_segment: int, dst_page: int):
        """Copy data from one page to another."""
        self.master.copyCalPage(src_segment, src_page, dst_segment, dst_page)

    def copy_segment(self, src_segment: int, dst_segment: int):
        """Copies all pages from one segment to another (where page numbers match)."""
        self._check_initialized()
        if src_segment not in self.segments or dst_segment not in self.segments:
            raise ValueError(f"Invalid segment number: {src_segment} or {dst_segment}")

        for page_nr in self.segments[src_segment].pages:
            if page_nr in self.segments[dst_segment].pages:
                self.copy_page(src_segment, page_nr, dst_segment, page_nr)

    def set_freeze_mode(self, segment: int, enabled: bool):
        """Enable or disable freeze mode for a segment."""
        self._check_initialized()
        if not self.freeze_supported:
            raise RuntimeError("Freeze mode not supported by slave.")

        mode = 1 if enabled else 0
        self.master.setSegmentMode(mode, segment)
        if segment in self.segments:
            self.segments[segment].mode = mode

    def is_frozen(self, segment: int) -> bool:
        """Check if a segment is in freeze mode."""
        mode = self.master.getSegmentMode(segment)
        return bool(mode & 0x01)

    def save_all(self):
        """Request the slave to save calibration data into non-volatile memory.

        For each segment in FREEZE mode, the slave saves the current active XCP page
        into the non-volatile memory (Page 0 of INIT_SEGMENT).
        """
        # SET_REQUEST: bit 0 is STORE_CAL_REQ
        self.master.setRequest(mode=0x01, session_configuration_id=0)

    def page_properties(self, segment: int, page: int) -> Optional["PagePropertiesInfo"]:
        """Return the cached :class:`~pyxcp.types.PagePropertiesInfo` for a page, or *None*.

        Parameters
        ----------
        segment : int
            Segment number.
        page : int
            Page number.
        """
        self._check_initialized()
        try:
            return self.segments[segment].pages[page].properties
        except KeyError:
            return None


#if !defined(__ALIGNED_BUFFER_HPP)
#define __ALIGNED_BUFFER_HPP

#include <variant>

#include <cstdint>
#include <cstdlib>
#include <vector>
#include <string_view>
#include <stdexcept>
#include <algorithm>
#include <cstring>

#include <pybind11/pybind11.h>

#if (defined(_WIN32) || defined(_WIN64)) && defined(_MSC_VER)
    #include <malloc.h>
#endif

namespace py = pybind11;

class AlignedBuffer {

public:

    AlignedBuffer(size_t size = 0xffff) : m_size(size), m_current_pos(0)  {
        m_buffer = nullptr;
        // Create naturally aligned buffer.
        constexpr std::size_t align = alignof(int);
        // aligned_alloc requires size to be a multiple of alignment.
        const std::size_t aligned_size = ((m_size + align - 1) / align) * align;
        #if (defined(_WIN32) || defined(_WIN64)) && defined(_MSC_VER)
        m_buffer = static_cast<uint8_t*>(::_aligned_malloc(aligned_size, align));
        #else
        m_buffer = static_cast<uint8_t*>(::aligned_alloc(align, aligned_size));
        #endif
    }

    AlignedBuffer(const AlignedBuffer& other) = delete;
    AlignedBuffer& operator=(const AlignedBuffer& other) = delete;
    AlignedBuffer(AlignedBuffer&& other) = delete;
    AlignedBuffer& operator=(AlignedBuffer&& other) = delete;

    ~AlignedBuffer() {
        if (m_buffer) {
            #if (defined(_WIN32) || defined(_WIN64)) && defined(_MSC_VER)
            ::_aligned_free(m_buffer);
            #else
            ::free(m_buffer);
            #endif
            m_buffer = nullptr;
        }
    }

    void reset() noexcept  {
        m_current_pos = 0;
    }

    std::size_t size() const noexcept {
        return m_current_pos;
    }

        // Get an element by index
    uint8_t get(size_t index) const {
        if (index >= size()) throw std::out_of_range("Index out of range");
        return m_buffer[index];
    }

    void append(uint8_t value) {
        if ((m_current_pos + 1) > m_size) {
            throw std::overflow_error("Buffer overflow");
        }
        m_buffer[m_current_pos] = value;
        m_current_pos++;
    }

    // Set an element by index
    void set(size_t index, uint8_t value) {
        if (index >= size()) throw std::out_of_range("Index out of range");
        m_buffer[index] = value;
    }

    static std::string_view bytes_as_string_view(const py::bytes& data) {
        char* buf = nullptr;
        Py_ssize_t len = 0;
        if (PyBytes_AsStringAndSize(data.ptr(), &buf, &len) != 0 || buf == nullptr || len < 0) {
            return std::string_view{};
        }
        return std::string_view(buf, static_cast<std::size_t>(len));
    }


    void extend(const py::bytes& values)  {
        auto data_view = bytes_as_string_view(values);

        if ((data_view.size() + m_current_pos) > m_size) {
            throw std::invalid_argument("Values vector is too large");
        }
        if (!data_view.empty()) {
            std::memcpy(m_buffer + m_current_pos, data_view.data(), data_view.size());
            m_current_pos += data_view.size();
        }
	}

	void extend(const std::vector<std::uint8_t>& values)  {
        if ((values.size() + m_current_pos) > m_size) {
            throw std::invalid_argument("Values vector is too large");
        }
        if (!values.empty()) {
            std::memcpy(m_buffer + m_current_pos, values.data(), values.size());
            m_current_pos += values.size();
        }
	}

    std::variant<uint8_t, py::bytes> get_item(py::object index) const {
        if (py::isinstance<py::slice>(index)) {
            py::slice slice = index.cast<py::slice>();
            size_t start, stop, step, length;
            if (!slice.compute(size(), &start, &stop, &step, &length)) {
                throw py::error_already_set();
            }
            return slice(start, stop, step);
        } else if (py::isinstance<py::int_>(index)) {
            Py_ssize_t idx = index.cast<Py_ssize_t>();
            if (idx < 0) {
                idx += static_cast<Py_ssize_t>(size());
            }
            if (idx < 0 || static_cast<std::size_t>(idx) >= size()) {
                throw std::out_of_range("Index out of range");
            }
            return get(static_cast<std::size_t>(idx));
        } else {
            throw py::type_error("Invalid index type");
        }
    }

    py::bytes slice(size_t start, size_t stop, size_t step) const {
        if (step == 0) {
            throw std::invalid_argument("Step cannot be zero");
        }
        // Clamp indices to valid range
        start = std::max(size_t(0), std::min(start, size_t(size())));
        stop = std::max(size_t(0), std::min(stop, size_t(size())));

        if (start >= stop) {
            return py::bytes("");
        }
        if (step == 1) {
            return py::bytes(reinterpret_cast<const char*>(m_buffer) + start, stop - start);
        }
        // General step handling (build result with stride)
        std::string out;
        out.reserve((stop - start + step - 1) / step);
        for (size_t i = start; i < stop; i += step) {
            out.push_back(static_cast<char>(m_buffer[i]));
        }
        return py::bytes(out);
    }

private:
    size_t m_size;
    size_t m_current_pos;
    uint8_t * m_buffer;
};


#endif // __ALIGNED_BUFFER_HPP

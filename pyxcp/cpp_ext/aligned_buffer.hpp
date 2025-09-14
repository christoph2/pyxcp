
#if !defined(__ALIGNED_BUFFER_HPP)
#define __ALIGNED_BUFFER_HPP

#include <variant>

#include <cstdint>
#include <cstdlib>

#if (defined(_WIN32) || defined(_WIN64)) && defined(_MSC_VER)
    #include <malloc.h>
#endif

namespace py = pybind11;

class AlignedBuffer {

public:

    AlignedBuffer(size_t size = 0xffff) : m_size(size), m_current_pos(0)  {
        m_buffer = nullptr;
        // Create natural aligned buffer.
        #if (defined(_WIN32) || defined(_WIN64)) && defined(_MSC_VER)
        m_buffer = static_cast<uint8_t*>(::_aligned_malloc(size, alignof(int)));
        #else
        m_buffer = static_cast<uint8_t*>(::aligned_alloc(alignof(int), size));
        #endif
    }

    AlignedBuffer(const AlignedBuffer& other) = delete;
    AlignedBuffer& operator=(const AlignedBuffer& other) = delete;
    AlignedBuffer(AlignedBuffer&& other) = delete;
    AlignedBuffer& operator=(AlignedBuffer&& other) = delete;

    ~AlignedBuffer() {
        if (m_buffer) {
            ::free(m_buffer);
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
        if ((m_current_pos + 1) >= m_size) {
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

    std::string_view bytes_as_string_view(const py::bytes& data) {
        return std::string_view{data};
    }


    void extend(/*const std::vector<std::uint8_t>*/const py::bytes& values) noexcept {
        auto data_view = bytes_as_string_view(values);

        if ((data_view.size() + m_current_pos) > m_size) {
            throw std::invalid_argument("Values vector is too large");
        }
		for (auto idx=0; idx < data_view.size(); ++idx) {
			m_buffer[m_current_pos] = data_view[idx];
			m_current_pos++;
		}
	}

	void extend(const std::vector<std::uint8_t>& values) noexcept {
        if ((values.size() + m_current_pos) > m_size) {
            throw std::invalid_argument("Values vector is too large");
        }
		for (auto idx=0; idx < values.size(); ++idx) {
			m_buffer[m_current_pos] = values[idx];
			m_current_pos++;
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
            size_t idx = index.cast<size_t>();
            if (idx < 0) {
                idx += size();
            }
            return get(idx);
        } else {
            throw py::type_error("Invalid index type");
        }
    }

    py::bytes slice(size_t start, size_t stop, size_t step) const {
        if (step == 0) {
            throw std::invalid_argument("Step cannot be zero");
        }
        if (start < 0) {
            start += size();
        }
        if (stop < 0) {
            stop += size();
        }

        // Clamp indices to valid range
        start = std::max(size_t(0), std::min(start, size_t(size())));
        stop = std::max(size_t(0), std::min(stop, size_t(size())));

        py::bytes result(reinterpret_cast<const char*>(m_buffer) + start, stop - start);
        return result;
    }

private:
    size_t m_size;
    size_t m_current_pos;
    uint8_t * m_buffer;
};


#endif // __ALIGNED_BUFFER_HPP

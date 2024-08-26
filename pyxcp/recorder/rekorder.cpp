
#define STANDALONE_REKORDER (1)

#include "rekorder.hpp"

void some_records(XcpLogFileWriter& writer) {
    const auto COUNT  = 1024 * 100 * 5;
    unsigned   filler = 0x00;
    char       buffer[1024];

    for (auto idx = 0; idx < COUNT; ++idx) {
        auto fr      = frame_header_t{};
        fr.category  = 1;
        fr.counter   = idx;
        fr.timestamp = std::clock();
        fr.length    = 10 + (rand() % 240);
        filler       = (filler + 1) % 16;
        memset(buffer, filler, fr.length);
        writer.add_frame(fr.category, fr.counter, fr.timestamp, fr.length, std::bit_cast<char const *>(&buffer));
    }
}

int main() {
    srand(42);

    printf("\nWRITER\n");
    printf("======\n");

    auto writer = XcpLogFileWriter("test_logger", 250, 1);
    some_records(writer);
    writer.finalize();

    printf("\nREADER\n");
    printf("======\n");

    auto reader = XcpLogFileReader("test_logger");
    auto header = reader.get_header();

    printf("size:               %u\n", header.hdr_size);
    printf("version:            %u\n", header.version);
    printf("options:            %u\n", header.options);
    printf("containers:         %u\n", header.num_containers);
    printf("records:            %u\n", header.record_count);
    printf("size/compressed:    %u\n", header.size_compressed);
    printf("size/uncompressed:  %u\n", header.size_uncompressed);
    printf("compression ratio:  %.2f\n", static_cast<float>(header.size_uncompressed) / static_cast<float>(header.size_compressed));

    while (true) {
        const auto& frames = reader.next_block();
        if (!frames) {
            break;
        }
        for (const auto& frame : frames.value()) {
            auto const& [category, counter, timestamp, length, payload] = frame;
        }
    }
    printf("---\n");
    printf("Finished.\n");
}

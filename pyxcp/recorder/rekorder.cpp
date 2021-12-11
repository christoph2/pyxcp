

#include "rekorder.hpp"

void some_records(XcpLogFileWriter& writer)
{
    const auto COUNT = 1024 * 10 * 5;
    auto my_frames = XcpFrames{};
    auto buffer = std::vector<char*>{};
    unsigned filler = 0x00;

    for (auto idx = 0; idx < COUNT; ++idx) {
        auto&& fr = FrameType{};
        fr.category = 1;
        fr.counter = idx;
        fr.timestamp = std::clock();
        fr.length = 10 + (rand() % 240);
        auto * payload = new char[fr.length];
        filler = (filler + 1) % 16;
        ::memset(&payload, filler, fr.length);
        buffer.emplace_back(payload);
        fr.payload = payload;
        my_frames.emplace_back(std::move(fr));
    }
    std::for_each(buffer.begin(), buffer.end(), [](char *v) {delete[] v;});
    writer.add_frames(my_frames);
    printf("Added %u frames.\n", my_frames.size());
}


int main(int argc, char *argv[])
{

    std::shared_ptr<char[]> sp(new char[1024]);

    auto arr_ptr1 = std::make_unique<int[]>(10);
    auto arr_ptr2 = std::make_shared<int[]>(10);

    srand(42);
#if 0
    auto writer = XcpLogFileWriter("test_logger");
    some_records(writer);
    writer.finalize();
#endif
    auto reader = XcpLogFileReader("test_logger");
    const auto& res = reader.next();
    printf("Finished.\n");
}


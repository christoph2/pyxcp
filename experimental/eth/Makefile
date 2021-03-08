INCLUDE= -I
CPPFLAGS += $(INCLUDE)

CFLAGS += -O3  -std=c11 -Wall -Wextra -Wno-unused-parameter -Wno-unused-function  -ffunction-sections
CXXFLAGS +=  -O3 -std=c++11 -Wall -Wextra -Wno-unused-parameter -Wno-unused-function  -ffunction-sections
LDFLAGS=  -Wl,-Map=$(xcp_sim_TARGET).map -Wl,--cref -Wl,-gc-sections -lws2_32

client_src = client.c common.c
client_objs = $(client_src:%.c=%.o)

server_src  = server.c common.c
server_objs = $(server_src:%.c=%.o)

all: client server

client_target=client
client: ${client_objs}

#g++ -Wall -std=c++14 -O3 -g win/timestamp.cpp -I. -Iwin/ -o timestamp.exe

server_target=server
server: ${server_objs}

%.o: %.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $(notdir $@)

$(client_target): $(client_objs)
	@echo Linking $(client_target)
	$(CC) $(CFLAGS) -o $(client_target) $(notdir $(client_objs)) $(LDFLAGS)

$(server_target): $(server_objs)
	@echo Linking $(server_target)
	$(CC) $(CFLAGS) -o $(server_target) $(notdir $(server_objs)) $(LDFLAGS)

clean:
	@rm -f $(client_objs) $(client_target).exe
	@rm -f $(server_objs) $(server_target).exe

.PHONY: clean all


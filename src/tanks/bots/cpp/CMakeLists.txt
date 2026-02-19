cmake_minimum_required(VERSION 3.15)
project(TanksBots VERSION 1.0 LANGUAGES CXX)

# C++17 required (for std::optional)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Include directories
include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

# Find nlohmann_json
# Option 1: Use FetchContent (recommended for self-contained builds)
include(FetchContent)
FetchContent_Declare(
    nlohmann_json
    URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
)
FetchContent_MakeAvailable(nlohmann_json)

# Option 2: If nlohmann_json is installed system-wide, uncomment:
# find_package(nlohmann_json 3.11.0 REQUIRED)

# Example bots
add_executable(simple_bot examples/simple_bot.cpp)
target_link_libraries(simple_bot PRIVATE nlohmann_json::nlohmann_json)

# Add more example bots here as needed
# add_executable(smart_bot examples/smart_bot.cpp)
# target_link_libraries(smart_bot PRIVATE nlohmann_json::nlohmann_json)

# Install targets
install(TARGETS simple_bot DESTINATION bin)

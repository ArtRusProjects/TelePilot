add_library(usermod_altaz INTERFACE)

target_sources(usermod_altaz INTERFACE
    ${CMAKE_CURRENT_LIST_DIR}/modaltaz.c
)

target_link_libraries(usermod INTERFACE usermod_altaz)
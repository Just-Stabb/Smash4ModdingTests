// latte-dis FILE OFFSET SIZE: disassemble a GX2 (Latte / R700) shader program from a file region
#include "latte/latte_disassembler.h"
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>
int main(int argc, char **argv)
{
   if (argc < 4) { std::fprintf(stderr, "latte-dis FILE OFFSET SIZE\n"); return 1; }
   std::ifstream f(argv[1], std::ios::binary);
   std::vector<uint8_t> d((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
   size_t off = std::strtoul(argv[2], nullptr, 0), size = std::strtoul(argv[3], nullptr, 0);
   if (off + size > d.size()) { std::fprintf(stderr, "out of range\n"); return 1; }
   std::cout << latte::disassemble(gsl::make_span(d.data() + off, size));
   return 0;
}

// decaf's assert hook (libcommon): report and stop
#include <string>
void assertFailed(const char *file, unsigned line, const char *expression, const std::string &message)
{
   std::fprintf(stderr, "assert %s:%u %s %s\n", file, line, expression, message.c_str());
   std::exit(2);
}

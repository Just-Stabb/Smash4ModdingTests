// decaf's common library pieces latte-asm needs (build_asm.sh)
#include <cstdio>
#include <cstdlib>
#include <string>

void assertFailed(const char *file, unsigned line, const char *expression, const std::string &message)
{
   std::fprintf(stderr, "assert %s:%u %s %s\n", file, line, expression, message.c_str());
   std::exit(2);
}

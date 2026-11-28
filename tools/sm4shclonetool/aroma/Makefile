#-------------------------------------------------------------------------------
# Sm4shCloneTool Aroma plugin (sm4shclonetool.wps)
#
# Needs devkitPPC, wut, the Wii U plugin system (WUPS) and Aroma's libkernel / libnotifications:
#   devkitPro pacman:  (dkp-)pacman -S wiiu-dev   (devkitPPC + wut)
#   WUPS, libkernel, libnotifications: the wiiu-env releases / docker images
#   (ghcr.io/wiiu-env/wiiupluginsystem, ghcr.io/wiiu-env/libkernel, ghcr.io/wiiu-env/libnotifications)
#   installed under $(DEVKITPRO)/wups and $(DEVKITPRO)/wums.
# Then:  make            (make CAVE_KB=2048 for a bigger code cave; the default 1024 KB fits ~140 fighter clones)
#-------------------------------------------------------------------------------
.SUFFIXES:

ifeq ($(strip $(DEVKITPRO)),)
$(error "Please set DEVKITPRO in your environment. export DEVKITPRO=<path to>/devkitpro")
endif

TOPDIR ?= $(CURDIR)

include $(DEVKITPRO)/wups/share/wups_rules

WUT_ROOT	:=	$(DEVKITPRO)/wut
WUMS_ROOT	:=	$(DEVKITPRO)/wums

TARGET		:=	sm4shclonetool
BUILD		:=	build
SOURCES		:=	src
DATA		:=
INCLUDES	:=	src
CAVE_KB		?=	1024

CFLAGS	:=	-g -Wall -O2 -ffunction-sections $(MACHDEP) -DCAVE_KB=$(CAVE_KB)
CFLAGS	+=	$(INCLUDE) -D__WIIU__ -D__WUT__ -D__WUPS__
CXXFLAGS	:=	$(CFLAGS)
ASFLAGS	:=	-g $(ARCH) -DCAVE_KB=$(CAVE_KB)
LDFLAGS	=	-g $(ARCH) $(RPXSPECS) -Wl,-Map,$(notdir $*.map) -T$(WUMS_ROOT)/share/libkernel.ld $(WUPSSPECS)

LIBS	:=	-lnotifications -lkernel -lwups -lwut
LIBDIRS	:=	$(PORTLIBS) $(WUMS_ROOT) $(WUPS_ROOT) $(WUT_ROOT)

ifneq ($(BUILD),$(notdir $(CURDIR)))

export OUTPUT	:=	$(CURDIR)/$(TARGET)
export TOPDIR	:=	$(CURDIR)
export VPATH	:=	$(foreach dir,$(SOURCES),$(CURDIR)/$(dir))
export DEPSDIR	:=	$(CURDIR)/$(BUILD)

CFILES		:=	$(foreach dir,$(SOURCES),$(notdir $(wildcard $(dir)/*.c)))
SFILES		:=	$(foreach dir,$(SOURCES),$(notdir $(wildcard $(dir)/*.S)))
export LD	:=	$(CC)
export OFILES	:=	$(CFILES:.c=.o) $(SFILES:.S=.o)
export INCLUDE	:=	$(foreach dir,$(INCLUDES),-I$(CURDIR)/$(dir)) \
			$(foreach dir,$(LIBDIRS),-I$(dir)/include) -I$(CURDIR)/$(BUILD)
export LIBPATHS	:=	$(foreach dir,$(LIBDIRS),-L$(dir)/lib)

.PHONY: $(BUILD) clean all

all: $(BUILD)

$(BUILD):
	@[ -d $@ ] || mkdir -p $@
	@$(MAKE) --no-print-directory -C $(BUILD) -f $(CURDIR)/Makefile

clean:
	@echo clean ...
	@rm -fr $(BUILD) $(TARGET).wps $(TARGET).elf

else
.PHONY: all

DEPENDS	:=	$(OFILES:.o=.d)

all: $(OUTPUT).wps

$(OUTPUT).wps: $(OUTPUT).elf
$(OUTPUT).elf: $(OFILES)

-include $(DEPENDS)

endif

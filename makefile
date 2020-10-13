
ALL_IMAGES =

define gen_aseprite_export
ALL_IMAGES += $(1)
$(1): $(2) makefile
	aseprite -b $(2) --scale $(3) --save-as $(1)

endef

# Level 1
$(eval $(call gen_aseprite_export,images/l1/chasm.gif,source_images/chasm.aseprite,4))
$(eval $(call gen_aseprite_export,images/l1/cliff_walk.png,source_images/cliff_walk.aseprite,2))
$(eval $(call gen_aseprite_export,images/l1/door.png,source_images/door.aseprite,4))
$(eval $(call gen_aseprite_export,images/l1/dungeon.gif,source_images/dungeon.aseprite,4))
$(eval $(call gen_aseprite_export,images/l1/key.gif,source_images/key.aseprite,6))

# Level 2 
$(eval $(call gen_aseprite_export,images/l2/ogre.gif,source_images/ogre.aseprite,6))
$(eval $(call gen_aseprite_export,images/l2/exit.png,source_images/exit.aseprite,4))

# Other
$(eval $(call gen_aseprite_export,readme_banner.gif,source_images/dungeon_logo.aseprite,4))
$(eval $(call gen_aseprite_export,website/gfx/banner.gif,source_images/dungeon_logo.aseprite,4))

.DEFAULT_GOAL := all
.PHONY: all
all: $(ALL_IMAGES)

.PHONY: clean
clean:
	rm $(ALL_IMAGES) >/dev/null 2>&1 || true

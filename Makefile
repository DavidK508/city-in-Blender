BLENDER ?= blender

.PHONY: preview preview-night render anim save clean

preview:
	$(BLENDER) --background --python run.py -- --preview

preview-night:
	$(BLENDER) --background --python run.py -- --preview --night

render:
	$(BLENDER) --background --python run.py -- --render

anim:
	$(BLENDER) --background --python run.py -- --anim

save:
	$(BLENDER) --background --python run.py -- --save

clean:
	rm -f renders/*.png renders/*.mp4 renders/*.blend

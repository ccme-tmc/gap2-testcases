PROJ = gap2-testcases
VERSION = $(shell \
		  awk '/__version__/ {printf("%s", $$3)}' gap_test.py | sed -e 's/"//g' \
		  )
BUILDTIME = $(shell date +'%Y-%m-%d %H:%M:%S')
MESSAGE_FILE = mcm.info
DIST_TARBALL = dist/$(PROJ)-$(VERSION).tar.gz
SED = gsed

include .objects

.PHONY: default dry dist clean veyrclean commit amend

default: dry

dry:
	python gap_test.py --init --dry

clean:
	find . -name "*.log" -delete
	find . -name "*.pyc" -delete
	find . -name ".coverage" -delete
	rm -rf dist __pycache__

veryclean: clean
	rm -rf inputs

commit:
	git commit -F $(MESSAGE_FILE)
	rm -f $(MESSAGE_FILE); touch $(MESSAGE_FILE)

amend:
	git commit --amend

dist: $(DIST_TARBALL)
	./dist.py

$(DIST_TARBALL): $(DIST_FILES)
	mkdir -p dist/$(PROJ)
	rsync -vazru --inplace --progress $^ dist/$(PROJ)/
	$(SED) "s/build time/build time: $(BUILDTIME)/g" \
		README.md > dist/$(PROJ)/README.md
	cd dist; tar --exclude=".DS_Store" \
		--exclude="*.pyc" --exclude="__pycache__" \
		--exclude="*.log" \
		--exclude=".git*" \
		-zcvf $(PROJ)-$(VERSION).tar.gz $(PROJ)
	rm -rf dist/$(PROJ)

push:
	@git push origin master

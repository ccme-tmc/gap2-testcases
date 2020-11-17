PROJ = gap2-testcases
VERSION = $(shell \
		  awk '/__version__/ {printf("%s", $$3)}' gap_test.py | sed -e 's/"//g' \
		  )
BUILDTIME = $(shell date +'%Y-%m-%d %H:%M:%S')
MESSAGE_FILE = mcm.info
DIST_TARBALL = dist/$(PROJ)-$(VERSION).tar.gz
SED = gsed

include .objects

.PHONY: default dry clean veyrclean cleanall commit amend push initall

default: dry

dry:
	python gap_test.py --init --dry
	python gap_test.py --dry

initall:
	python gap_test.py --init

initgap:
	python gap_test.py --init-gap

clean:
	find . -name "*.log" -delete
	find . -name "*.pyc" -delete
	find . -name ".coverage" -delete
	rm -rf dist __pycache__

veryclean: clean
	rm -rf inputs workspace

cleanall: veryclean

commit:
	git commit -t $(MESSAGE_FILE)
	rm -f $(MESSAGE_FILE); touch $(MESSAGE_FILE)

amend:
	git commit --amend

remote: $(DIST_TARBALL)
	python dist.py

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

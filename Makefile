UPDATE_LIB_FILE=username_update_lib.py
XPRO_UPDATER_SCRIPT=xpro_username_update
XPRO_SPECIFIC_USER_UPDATER_SCRIPT=xpro_specific_username_update
EDX_UPDATER_SCRIPT=edx_username_update
EDX_FORUM_UPDATER_SCRIPT=edx_forum_username_update

checkenv :
ifndef UPDATE_REPO_PATH
	@echo "Need to set UPDATE_REPO_PATH env var"; exit 1;
endif

cleanup.xpro :
	rm -f ./$(UPDATE_LIB_FILE) ./$(XPRO_UPDATER_SCRIPT).py ./$(XPRO_SPECIFIC_USER_UPDATER_SCRIPT).py

cleanup.edx :
	rm -f ./$(UPDATE_LIB_FILE) ./$(EDX_UPDATER_SCRIPT).py ./$(EDX_FORUM_UPDATER_SCRIPT).py;

setup.xpro : checkenv cleanup.xpro
	cp $(UPDATE_REPO_PATH)/$(UPDATE_LIB_FILE) . && \
		cp $(UPDATE_REPO_PATH)/$(XPRO_UPDATER_SCRIPT).py . && \
		cp $(UPDATE_REPO_PATH)/$(XPRO_SPECIFIC_USER_UPDATER_SCRIPT).py .

setup.edx : checkenv cleanup.edx
	cp $(UPDATE_REPO_PATH)/$(UPDATE_LIB_FILE) . && \
		cp $(UPDATE_REPO_PATH)/$(EDX_UPDATER_SCRIPT).py . && cp $(UPDATE_REPO_PATH)/$(EDX_FORUM_UPDATER_SCRIPT).py .

run.xpro :
	@echo "import $(XPRO_UPDATER_SCRIPT)" | python ./manage.py shell

run.xpro.specific :
	@echo "import $(XPRO_SPECIFIC_USER_UPDATER_SCRIPT)" | python ./manage.py shell

run.edx :
	@echo "import $(EDX_UPDATER_SCRIPT)" | python ./manage.py lms shell

run.edx.forum :
	@echo "import $(EDX_FORUM_UPDATER_SCRIPT)" | python ./manage.py lms shell

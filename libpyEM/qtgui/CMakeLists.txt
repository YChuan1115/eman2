FILE(GLOB qtguifiles "${CMAKE_CURRENT_SOURCE_DIR}/*.py")
FILE(GLOB exclusionlist "em3Dhelloworld.py")

# MESSAGE("gui files: ${qtguifiles}")

LIST(REMOVE_ITEM qtguifiles ${exclusionlist})

# MESSAGE("reduced gui files: ${qtguifiles}")

# INSTALL(FILES ${qtguifiles} DESTINATION lib)

SET (DBG $ENV{DEBUG})

FOREACH(f ${qtguifiles})
	INSTALL(FILES ${f} DESTINATION ${EMAN_PY_INSTALL_PREFIX})
	IF(DBG MATCHES "y")
		MESSAGE("Copied Qt GUI file ${f} to ${EMAN_PY_INSTALL_PREFIX}")
	ENDIF(DBG MATCHES "y")
ENDFOREACH(f)

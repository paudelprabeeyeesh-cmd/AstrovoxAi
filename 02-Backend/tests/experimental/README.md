# Experimental tests

These tests cover experimental modules listed in docs/MODULE_INVENTORY.md.
They are not part of the product test suite: their import surface has drifted
from the packages they exercise, so they are excluded from collection by

orecursedirs in pytest.ini.

Keep them for reference while the experimental modules are rebuilt. Moving one
back into 	ests/ re-enables it in the product suite, which will fail until the
import surface is fixed.
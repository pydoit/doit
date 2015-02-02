.PHONY: tmp1_phony
tmp1_phony:
	echo hi1 > tmp1_phony

tmp2_phony: tmp1_phony
	echo hi2 > tmp2_phony

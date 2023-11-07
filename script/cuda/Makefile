FIRST: testout.txt

runs.o: runs.cu
	nvcc -c -o runs.o runs.cu --compiler-options -fPIC

librangeruns.so: runs.o
	gcc -shared -fPIC -o librangeruns.so runs.o -L/usr/local/cuda/lib64/ -lcuda -lcudart -lstdc++

.PHONY:
	exit 0

testout.txt: .PHONY librangeruns.so
	python3 ./test_runs.py 2>&1 | tee testout.txt

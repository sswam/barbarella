./run_batches.py -n 5 -- ./flash_gen.sh -n= -extra="Please make one numbered flashcard note corresponding to each numbered topic in the input. In the extra section, include interesting examples using other Python libraries and diverse applications. Mix it up a lot and make it creative and interesting. I am interested in deep learning work and need to learn the basics properly. If it helps you to be more random, try to use a library starting with the first letter in the term." -- - < numpy_topics.md | tee notes-numpy.txt
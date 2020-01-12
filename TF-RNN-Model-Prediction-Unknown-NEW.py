# Implementation of an artificial neural network
# Load all necessary libraries
import sys
from os import path
import tensorflow as tf
import numpy as np
np.set_printoptions(threshold=sys.maxsize)
from datetime import datetime 
from Bio import SeqIO
import gzip
import shutil
import re


# Function to generate batches of data
def create_batch_generator(x, y=None, batch_size=64):
    # get the number of batches of size 64 given the size of the training dataset
    n_batches = len(x)//batch_size # 2 / will round the float number to an integer
    # create empty array to store y values in case it is not none
    y_copy = np.empty([1, n_batches*batch_size])
    if y is not None:
        y_copy = np.array(y)
        y_copy = y_copy[:n_batches*batch_size]
    # create batch from reduced training set 
    x_copy = np.array(x)
    x_copy = x_copy[:n_batches*batch_size]
    for i in range(0, x_copy.shape[0], batch_size):
        if y is not None:
            yield (x_copy[i:i+batch_size, :], y_copy[i:i+batch_size])
        else:
            yield x_copy[i:i+batch_size, :]

            
def model_performance(preds, probs, ListReadsID, FileFastq, Reads_dict, class_mapping):
    # Create dictionary with number of reads assigned to each class
    DictProbs = {} # key = order, value = list of probabilities for each read predicted
    ListProbsReadsDropped = []
    for i in range(len(preds)):
        prediction = probs[i][preds[i]]
        # Get only prediction with probability above 50%
        if prediction <= 0.5:
            ListProbsReadsDropped.append(probs[i])
            continue
        
         # Get Order predicted
         predOrder = class_mapping[preds[i]]
         # Add read to corresponding file
         with gzip.open('/users/ccres/data/ccres/Model-Cheyenne-150bp/Testing/ZachReads/Batch1/QCedReads/FastqOUT_Reads/{0}-Reads-{1}.fq.gz'.format(FileFastq.split(".")[0],predOrder), 'at') as ReadsClassified:
            # Create an instance with fastq reads information
            if ListReadsID[i] in Reads_dict:
               seq_record = Reads_dict[ListReadsID[i]]
               ReadsClassified.write(seq_record.format('fastq'))
             # add read to DictProbs
             if predOrder not in DictProbs:
                DictProbs[predOrder] = []
             DictProbs[predOrder].append(prediction)

    ResultsFile = open('/users/ccres/data/ccres/Model-Cheyenne-150bp/Testing/ZachReads/Batch1/QCedReads/Predictions-{}.txt'.format(FileFastq.split(".")[0]),'a+')
    ResultsFile.write('Train set: ' + str(24) + '\t' + 'Checkpoint File: ' +  str(77) + '\t' + 'Number of reads tested: ' + str(len(preds)) + '\n')
    for OrderName, ListProbs in DictProbs.items():
        ResultsFile.write(str(OrderName) + '\t' + 'Number of Reads: ' + str(len(ListProbs)) + '\t')
        for prob in ListProbs:
            ResultsFile.write(str(prob) + '\t')
        ResultsFile.write('\n')

        
def createMatrix(DictVectors, sequence_length):
    # Create a list with the reads id
    #ListReadsID = list(DictVectors.keys())
    # Create matrix of zeros, where each row corresponds to a read (vector of kmers)
    #sequences = np.zeros((len(DictVectors), sequence_length), dtype=int)
    # Replace array in corresponding position in sequences matrix
    # (the index of the read in ListReadsID corresponds to the position of it's kmer vector
    # in the sequences matrix)
    #for i in range(len(ListReadsID)):
    #    sequences[i] = DictVectors[ListReadsID[i]]
    sequences = np.full((len(DictVectors), sequence_length), list(DictVectors.values()))
    return sequences, ListReadsID


def get_all_kmers(list_nt, prefix, n, k, list_kmers):
    if k == 0:
        return list_kmers.append(prefix)
    for i in range(n):
        newPrefix = prefix + list_nt[i]
        get_all_kmers(list_nt, newPrefix, n, k-1, list_kmers)

        
# Function that looks for any characters different 
# from A, C, T or G and converts the DNA sequence into a vector of 10-mers 
def ParseSeq(DNAsequence,kmers_dict):
    # create empty list to store all the kmers
    listKmers = []
    # Drop the read if it contains letters other than A, C, T or G
    if not re.match('^[ATCG]+$', DNAsequence):
        return listKmers
    # Creates a sliding window of width 10
    for n in range(len(DNAsequence) - 9):
        kmer = DNAsequence[n:n+10]
        # Lookup integer mapped to the kmer
        kmer_Integer = kmers_dict[kmer]
        # Add kmer to vector of kmer
        listKmers.append(kmer_Integer)
    # Pad or truncate list to 141 kmers
    listKmers = listKmers[:141] + [0]*(141 - len(listKmers))
    # transform list into numpy array
    array_int = np.asarray(listKmers)
    # Flip array
    array_int = np.flip(array_int, axis=0)
    return array_int


def GetKmersDictionary(k_value=10):
    # Create empty list to store all possible kmers
    list_kmers = []
    list_nt = ['A', 'T', 'C', 'G']
    # Get list of all possible 4**k_value kmers
    get_all_kmers(list_nt, "", len(list_nt), k_value, list_kmers)
    # generate a list of integers
    list_num = list(range(0,len(list_kmers)))
    # Assign an integer to each kmer
    kmers_dict = dict(zip(list_kmers, list_num))
    return kmers_dict


# Goes through the fastq file to create the dictionary
def ParseFastq(Reads_dict, kmers_dict):
    DictVectors = {} # keys = read_id, value = array of integer
    for record in Reads_dict.keys():
        # Check read sequence
        seq_record = Reads_dict[record]
        KmerVector = ParseSeq(str(seq_record.seq), kmers_dict)
        if len(KmerVector) == 141:
            DictVectors[record] = KmerVector
    print(f'Total number of reads: {len(Reads_dict)}')
    print(f'Number of reads after processing: {len(DictVectors)}')
    return DictVectors


# Unzip the .gz file for SeqIO.index command
def unzipFile(FastqFile, FileName):
    with gzip.open(FastqFile, 'rb') as zippedFastq:
        with open(FileName, 'wb') as unzippedFastq:
            shutil.copyfileobj(zippedFastq, unzippedFastq)

def main():
    # Set model parameters
    embedding_size = 6
    num_layers = 1
    lstm_size = 256
    learning_rate = 0.0001
    num_epochs = 5
    batch_size = 64
    k_value = 10
    num_kmers = 4**k_value
    num_classes = 8
    sequence_length = int(150 - k_value + 1)
    
    # Exception handling for number of arugments
    if len(sys.argv) != 3:
        sys.exit("Incorrect number of arguments provided.\nCorrect format: [script] [read] [num of threads]\n")
        
    print(f'\nProcess reads: START -- {datetime.now()}')
    # Get fastq file name
    FastqFile = str(sys.argv[1])
    print(f'Fastq File: {FastqFile}')
    
    # Get filename 
    FileName = FastqFile.split(".gz")[0]
    print(f'File Name: {FileName}')
    
    # Unzip the file
    unzipFile(FastqFile, FileName)
    
    # Parse Fastq file
    kmers_dict = GetKmersDictionary()
    Reads_dict = SeqIO.index(FileName, 'fastq') 
    DictVectors = ParseFastq(Reads_dict, kmers_dict)
    
    # Create matrix
    X_test, ListReadsID = createMatrix(DictVectors, sequence_length)
    print("\nProcess reads: END -- {}".format(datetime.now()), file=sys.stderr)

    # Get order names mapped to integers
    class_mapping = {0: 'Enterobacterales', 1: 'Mycoplasmatales', 2: 'Chlamydiales', 3: 'Vibrionales',
                     4: 'Fusobacteriales', 5: 'Spirochaetales', 6: 'Rhodobacterales', 7: 'Unclassified'}
    print(f'class_mapping dictionary: {class_mapping}\n')
    
    # reset graph
    tf.compat.v1.reset_default_graph()
    
    # Create new empty computation graph
    g = tf.Graph()
    # Define model
    with g.as_default():
        # Set a graph-level seed to make the random sequences generated by all operations be repeatable across sessions
        tf.compat.v1.set_random_seed(123)
        with tf.device('/device:GPU:0'):
            # Define the placeholders for holding the input values: sequences of unique kmers (tf_x) 
            # and the response values (tf_y)
            tf_x = tf.compat.v1.placeholder(tf.int32, [batch_size, sequence_length], 'tf_x')
            tf_y = tf.compat.v1.placeholder(tf.int32, [batch_size], 'tf_y')
            tf_keepprob = tf.compat.v1.placeholder(tf.float32, name='tf_keepprob')

            # Convert labels to a one-hot representation (necessary to use the cost function)
            y_onehot = tf.one_hot(indices=tf_y, depth=num_classes)
          
            # Create embedding layer: Create a matrix of size [n_kmers x embedding_size] as a tensor variable and initialize its elements
            # randomly with floats between [-1,1]
            embedding = tf.Variable(tf.random.uniform((num_kmers, embedding_size), minval=-1, maxval=1), name='embedding')
            embed_x = tf.nn.embedding_lookup(embedding, tf_x, name='embeded_x')
            
            # define LSTM cell and stack them together
            # BasicLSTMCell wrapper class that defines LSTM cells which can be stacked together to form a multilayer RNN
            # using the MultiRNNCell wrapper class, apply dropout (NN regularization) to each layer
            # make a list using python list comprehension of LSTM cells according to the desired number of RNN layers
            cells = tf.compat.v1.nn.rnn_cell.MultiRNNCell([tf.compat.v1.nn.rnn_cell.DropoutWrapper(
                    tf.compat.v1.nn.rnn_cell.LSTMCell(lstm_size,state_is_tuple=True), 
                    output_keep_prob=tf_keepprob)for i in range(num_layers)])

            # Define the initial state (there are 3 types of inputs in LSTM cells: input data x (embed_x data tensor), 
            # activations of hidden units
            # from the previous time step h and the cell state from the previous time step C)
            saved_state = tf.compat.v1.get_variable('saved_state', shape=[num_layers, 2, batch_size, lstm_size], dtype=tf.float32)
            state_placeholder = tf.compat.v1.placeholder(tf.float32, [num_layers, 2, batch_size, lstm_size], name='state_placeholder')
            l = tf.unstack(state_placeholder, axis=0)
            tuple_initial_state = tuple([tf.compat.v1.nn.rnn_cell.LSTMStateTuple(l[idx][0],l[idx][1])for idx in range(num_layers)])
            print(f'\n<< initial state >> {tuple_initial_state}')
            
            # the tf.nn.dynamic_rnn function pulls the embedded data, the RNN cells and their initial states and creates
            # a pipeline for them according to the architecture of LSTM cells
            # We store the final state to use  as the initial state of the next mini-batch of data
            lstm_outputs, final_state = tf.compat.v1.nn.dynamic_rnn(cells, embed_x, initial_state=tuple_initial_state)
            assign_state = tf.compat.v1.assign(saved_state, final_state, name='assign_state')

            # the tf.nn.dynamic_rnn function returns a tuple containing the activations of the RNN cells: outputs and their
            # final state: state. The output is a 3 dimensional tensor with the following shape:
            # lstm_outputs shape: [batch_size, max_time, cells.output_size]
            print(f'\n<< lstm_output >> {lstm_outputs}')
            print(f'\n<< final state >> {final_state}')
            print(f'{lstm_outputs[:, -1]}')
            
            # Pass outputs to a connected layer to get logits 
            logits = tf.compat.v1.layers.dense(inputs=lstm_outputs[:, -1], units=num_classes, activation=None, name='logits')
            print(f'\n<< logits >> {logits}')
            y_proba = tf.nn.softmax(logits, name='probabilities')
            predictions = {
                'labels': tf.argmax(logits, axis=1, name='labels'),
                'probabilities': y_proba
            }
            print(f'\n<< predictions >> {predictions}')
            # Define the cost function
            cost = tf.reduce_mean(
                tf.nn.softmax_cross_entropy_with_logits(
                logits=logits, labels=y_onehot),
                name='cost')
            print(f'\n<< cost >> {cost}')
            # Define the optimizer
            optimizer = tf.train.AdamOptimizer(learning_rate)
            train_op = optimizer.minimize(cost, name='train_op')
        # Create saver object
        saver = tf.train.Saver()
        # Returns an Operation that initializes global variables in the graph
        init_op = tf.global_variables_initializer()
    
    # Test model with testing set
    print("\nStart testing: {}".format(datetime.now()), file=sys.stderr)
    with tf.Session(graph = g) as sess:
        latest_ckp = '/users/ccres/data/ccres/Model-Cheyenne-150bp/model-8orders-sw-k10-balanced/SpeciesRNN-sw-8orders-10-77.ckpt'
        print(latest_ckp, file=sys.stderr)
        saver = tf.train.import_meta_graph('/users/ccres/data/ccres/Model-Cheyenne-150bp/model-8orders-sw-k10-balanced/SpeciesRNN-sw-8orders-10-77.ckpt.meta')
        # restore the saved variable
        saver.restore(sess, latest_ckp)
        print('Model restored')
        # Get embeddings
        embeddingsValues = sess.run('embedding:0')
        print(embeddingsValues[0])
        for kmerString, kmerValue in kmers_dict.items():
            if kmerValue == 0:
                print('embedding of k-mer {0} with integer value {1} is {2}'.format(kmerString, kmerValue, embeddingsValues[kmerValue]))
                break
        
        preds = []  # keep test accuracy after each epoch for testing set
        probs = []
        test_state = np.zeros((num_layers, 2, batch_size, lstm_size))
        batch_generator_validation = create_batch_generator(X_test, None, batch_size=batch_size)
        for batch_x_test in batch_generator_validation:
            feed_val = {'tf_x:0':batch_x_test, 'tf_keepprob:0': 1.0, 'state_placeholder:0':test_state}
            pred, test_state, prob = sess.run(['labels:0', saved_state, 'probabilities:0'], feed_dict=feed_val)
            preds.append(pred)
            probs.append(prob)
        all_preds = np.concatenate(preds)
        all_probs = np.concatenate(probs)
        print('Size all_probs vector: {}'.format(len(all_probs)))
        print('Size all_preds vector: {}'.format(len(all_preds)))
        # Get performance statistics for each order
        model_performance(all_preds, all_probs, ListReadsID, FastqFile, Reads_dict, class_mapping)
    print("\nEnd testing: {}".format(datetime.now()), file=sys.stderr)


# In[13]:


if __name__ == "__main__":
    main()


import tensorflow as tf


def categorical(probs, size=1):
	logits = tf.math.log(probs)[None,:]
	return tf.squeeze(tf.random.categorical(logits, num_samples=size), axis=0)

def randint(high, size=(), dtype=tf.int64):
	return tf.random.uniform(size, maxval=high, dtype=dtype)

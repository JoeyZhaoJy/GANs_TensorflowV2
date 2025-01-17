from __future__ import absolute_import, division, print_function, unicode_literals
"""
基于tensorflow 高阶API
SGAN  标准GAN  standard GAN 
损失函数: 经典log损失 即交叉熵损失 对抗损失 赋予正负样本 1 0 标签后的推导值 其实就是交叉熵 只是分开了正负样本
        但是基于tensorflow的交叉熵计算时优化过的 对于log(0)不会出现无穷值 这就是我自己的log函数容易崩坏的原因
网络结构: 多层的卷积形式 
数据形式: 带卷积层 数据映射到-1 1 区间
生成器: tanh 映射到-1 1 之间 迎合数据格式
判别器: sigmoid 映射到0 1 之间 迎合loss公式的约束
初始化: xavier初始化  即考虑输入输出维度的 glorot uniform
训练： 判别器和生成器同时训练 同步训练 不偏重任一方
"""
import my_mnist  
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import my_layers
from tensorflow.keras import layers
import time
(train_images,train_labels),(_, _) = my_mnist.load_data(get_new=False,
                                                        normalization=False,
                                                        one_hot=True,
                                                        detype=np.float32)
train_images = (train_images.astype('float32')-127.5)/127.5
train_labels = (train_labels.astype('float32')-0.5)/0.5                                                    
train_images = train_images.reshape(train_images.shape[0], 28, 28,1)
print(train_labels[0])
plt.imshow(train_images[0, :, :,0], cmap='gray')
plt.show()

    

class Discriminator(tf.keras.Model):
    def __init__(self,in_shape):
        super(Discriminator,self).__init__()
        """
        反卷积和dense层采用偏置 各自2参数 
        2+2+2=6 一共六个参数个数(指独立大参数self.w self.b的个数)
        """
        self.Conv2d_1 = my_layers.Conv2D(input_shape=in_shape,out_depth=64,filter_size=[5,5],strides=[2,2],use_bias=True,pandding_way="SAME")
        self.LeakyReLU_1 = my_layers.LeakyReLU(in_shape=self.Conv2d_1.out_shape)
        self.DropOut_1 = my_layers.Dropout(in_shape=self.LeakyReLU_1.out_shape,dropout_rate=0.3)
        
        self.Conv2d_2 = my_layers.Conv2D(input_shape=self.DropOut_1.out_shape,out_depth=128,filter_size=[5,5],strides=[2,2],use_bias=True,pandding_way="SAME")
        self.LeakyReLU_2 = my_layers.LeakyReLU(in_shape=self.Conv2d_2.out_shape)
        self.DropOut_2= my_layers.Dropout(in_shape=self.LeakyReLU_2.out_shape,dropout_rate=0.3)
        next_shape = 1
        for i in self.DropOut_2.out_shape:
            next_shape *= i 
        self.Dense = my_layers.Dense(next_shape,units=1)
    @tf.function
    def call(self,x,training=True):
        conv2_l1 = self.Conv2d_1(x)
        leakey_relu_l1 = self.LeakyReLU_1(conv2_l1,training)
        dropout_l1 = self.DropOut_1(leakey_relu_l1,training)
        conv2_l2 = self.Conv2d_2(dropout_l1)
        leakey_relu_l2 = self.LeakyReLU_2(conv2_l2,training)
        dropout_l2 = self.DropOut_2(leakey_relu_l2,training)
        dense_l3 =  self.Dense(tf.reshape(dropout_l2,[dropout_l2.shape[0],-1]),training)
        l3_out = tf.nn.sigmoid(dense_l3)
        return l3_out

d = Discriminator(in_shape=[28,28,1])
x = train_images[0:128, :, :,:]
print(d(x,training=False))#行向量统一输入  而batch是行向量在列方向堆叠后的矩阵 
# print(d(x,training=True))#行向量统一输入  而batch是行向量在列方向堆叠后的矩阵 
print(len(d.trainable_variables))

class Generator(tf.keras.Model):
    def __init__(self,in_dim):
        super(Generator,self).__init__()
        """
        bn层两个参数 
        反卷积和dense层不采用偏置 各自只有一个参数 
        1+2+1+2+1+2+1=10 一共十个参数个数(指独立大参数self.w self.b的个数)
        """
        self.Dense_1 = my_layers.Dense(in_dim,7*7*256,use_bias=False)
        self.BacthNormalization_1 = my_layers.BatchNormalization(in_shape=self.Dense_1.out_dim)
        self.LeakyReLU_1 = my_layers.LeakyReLU(in_shape=self.BacthNormalization_1.out_shape)
        
        self.Conv2dTranspose_2 = my_layers.Conv2DTranspose(in_shape=[7,7,256],out_depth=128,kernel_size=[5,5],strides=[1,1],pandding_way="SAME",use_bias=False) 
        assert self.Conv2dTranspose_2.out_shape == [7,7,128]
        self.BacthNormalization_2 = my_layers.BatchNormalization(in_shape=self.Conv2dTranspose_2.out_shape)
        self.LeakyReLU_2 = my_layers.LeakyReLU(in_shape=self.BacthNormalization_2.out_shape)

        self.Conv2dTranspose_3 = my_layers.Conv2DTranspose(in_shape=self.LeakyReLU_2.out_shape,out_depth=64,kernel_size=[5,5],strides=[2,2],pandding_way="SAME",use_bias=False) 
        assert self.Conv2dTranspose_3.out_shape == [14,14,64]
        self.BacthNormalization_3 = my_layers.BatchNormalization(in_shape=self.Conv2dTranspose_3.out_shape)
        self.LeakyReLU_3 = my_layers.LeakyReLU(in_shape=self.BacthNormalization_3.out_shape)

        self.Conv2dTranspose_4 = my_layers.Conv2DTranspose(in_shape=self.LeakyReLU_3.out_shape,out_depth=1,kernel_size=[5,5],strides=[2,2],pandding_way="SAME",use_bias=False) 
        assert self.Conv2dTranspose_4.out_shape == [28,28,1]
    @tf.function
    def call(self,x,training=True):
        dense_l1 = self.Dense_1(x,training)
        #tf.print(dense_l1)
        bn_l1 = self.BacthNormalization_1(dense_l1,training)
        #tf.print(bn_l1) batch_normalization 在训练时 如果batch sizez是1 则会直接归零 因为会减去均值
        lr_l1 = self.LeakyReLU_1(bn_l1,training)
        #tf.print(lr_l1)
        conv2d_tr_l2 = self.Conv2dTranspose_2(tf.reshape(lr_l1,[-1,7,7,256]))
        bn_l2 = self.BacthNormalization_2(conv2d_tr_l2,training)
        lr_l2 = self.LeakyReLU_2(bn_l2,training)

        conv2d_tr_l3 = self.Conv2dTranspose_3(lr_l2)
        bn_l3 = self.BacthNormalization_3(conv2d_tr_l3,training)
        lr_l3 = self.LeakyReLU_3(bn_l3,training)

        conv2d_tr_l4 = self.Conv2dTranspose_4(lr_l3)
        l4_out = tf.nn.tanh(conv2d_tr_l4)
        return l4_out

g = Generator(100)
z = tf.random.normal((2,100))

image = g(z,training=False)
for i in range(image.shape[0]):
    plt.imshow(tf.reshape(image[i],(28,28)), cmap='gray')
    plt.show()

# image = g(z,training=True)
# for i in range(image.shape[0]):
#     plt.imshow(tf.reshape(image[i],(28,28)), cmap='gray')
#     plt.show()
print(len(g.trainable_variables))
print(d(image,training=False))

cross_entropy = tf.keras.losses.BinaryCrossentropy(from_logits=False)#判别器已经sigmoid 所以是false
def d_loss(real_output, fake_output):
    real_loss = cross_entropy(tf.ones_like(real_output),real_output)
    fake_loss = cross_entropy(tf.zeros_like(fake_output),fake_output)
    total_loss = real_loss + fake_loss
    return total_loss
def g_loss(fake_output):
    return cross_entropy(tf.ones_like(fake_output),fake_output)

generator_optimizer = tf.keras.optimizers.Adam(1e-4)
discriminator_optimizer = tf.keras.optimizers.Adam(1e-4)

EPOCHS = 50
BATCH_SIZE = 128
z_dim = 100
num_examples_to_generate = 100
# seed = tf.random.normal([num_examples_to_generate, z_dim],mean=0.0,stddev=1.0)
seed = tf.random.uniform([num_examples_to_generate, z_dim],-1.0,1.0)



@tf.function
def train_step(images,labels):
    # z = tf.random.normal([images.shape[0], z_dim],mean=0.0,stddev=1.0)
    z = tf.random.uniform([images.shape[0], z_dim],-1.0,1.0)
    with tf.GradientTape() as gen_tape, tf.GradientTape() as disc_tape:
        generated_images = g(z,training=True)
        real_output = d(images,training=True)
        fake_output = d(generated_images,training=True)
        gen_loss = g_loss(fake_output)
        disc_loss = d_loss(real_output,fake_output)
    gradients_of_generator = gen_tape.gradient(gen_loss, g.trainable_variables)
    gradients_of_discriminator = disc_tape.gradient(disc_loss, d.trainable_variables)
    generator_optimizer.apply_gradients(zip(gradients_of_generator, g.trainable_variables))
    discriminator_optimizer.apply_gradients(zip(gradients_of_discriminator, d.trainable_variables))

def train(train_images,train_labels,epochs):
    index = list(range(train_images.shape[0]))
    np.random.shuffle(index)
    train_images = train_images[index]
    train_labels = train_labels[index]
    images_batches = iter(tf.data.Dataset.from_tensor_slices(train_images).batch(BATCH_SIZE))
    labels_batches = iter(tf.data.Dataset.from_tensor_slices(train_labels).batch(BATCH_SIZE))
    for epoch in range(epochs):
        start = time.time()
        while True:
            try:
                x_real_bacth = next(images_batches)
                y_label_bacth = next(labels_batches)
                train_step(x_real_bacth,y_label_bacth)
            except StopIteration:
                del images_batches
                del labels_batches
                np.random.shuffle(index)
                train_images = train_images[index]
                train_labels = train_labels[index]
                images_batches = iter(tf.data.Dataset.from_tensor_slices(train_images).batch(BATCH_SIZE))
                labels_batches = iter(tf.data.Dataset.from_tensor_slices(train_labels).batch(BATCH_SIZE))
                break
        generate_and_save_images(g,epoch + 1,seed)
        print ('Time for epoch {} is {} sec'.format(epoch + 1, time.time()-start))
def generate_and_save_images(model, epoch, test_input):
    predictions = model(test_input,training=False)
    plt.figure(figsize=(10,10))
    for i in range(predictions.shape[0]):
        plt.subplot(10,10,i+1)
        plt.imshow(tf.reshape(predictions[i,:],shape=(28,28))*127.5+127.5, cmap='gray')
        plt.axis('off')
    plt.savefig('./DCGAN/image_at_epoch_{:04d}.png'.format(epoch))
    plt.close()

print(time)
train(train_images,train_labels,EPOCHS)
import math
import os
import cv2
import numpy


class Classification:
    def __init__(self, onnx_path, session=None):
        self.session = session
        if self.session is None:
            assert onnx_path is not None
            assert os.path.exists(onnx_path)
            from onnxruntime import InferenceSession
            self.session = InferenceSession(onnx_path,
                                            providers=['CUDAExecutionProvider'])
        self.inputs = self.session.get_inputs()[0]
        self.threshold = 0.98
        self.labels = ['0', '180']

    @staticmethod
    def resize(image):
        input_c = 3
        input_h = 48
        input_w = 192
        h = image.shape[0]
        w = image.shape[1]
        ratio = w / float(h)
        if math.ceil(input_h * ratio) > input_w:
            resized_w = input_w
        else:
            resized_w = int(math.ceil(input_h * ratio))
        resized_image = cv2.resize(image, (resized_w, input_h))

        if input_c == 1:
            resized_image = resized_image[numpy.newaxis, :]

        resized_image = resized_image.transpose((2, 0, 1))
        resized_image = resized_image.astype('float32')
        resized_image = resized_image / 255.0
        resized_image -= 0.5
        resized_image /= 0.5
        padded_image = numpy.zeros((input_c, input_h, input_w), dtype=numpy.float32)
        padded_image[:, :, 0:resized_w] = resized_image
        return padded_image

    def __call__(self, images):
        num_images = len(images)

        results = [['', 0.0]] * num_images
        indices = numpy.argsort(numpy.array([x.shape[1] / x.shape[0] for x in images]))

        batch_size = 6
        for i in range(0, num_images, batch_size):

            norm_images = []
            for j in range(i, min(num_images, i + batch_size)):
                norm_img = self.resize(images[indices[j]])
                norm_img = norm_img[numpy.newaxis, :]
                norm_images.append(norm_img)
            norm_images = numpy.concatenate(norm_images)

            outputs = self.session.run(None,
                                       {self.inputs.name: norm_images})[0]
            outputs = [(self.labels[idx], outputs[i, idx]) for i, idx in enumerate(outputs.argmax(axis=1))]
            for j in range(len(outputs)):
                label, score = outputs[j]
                results[indices[i + j]] = [label, score]
                if '180' in label and score > self.threshold:
                    images[indices[i + j]] = cv2.rotate(images[indices[i + j]], 1)
        return images, results

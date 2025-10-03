import math
import os
import cv2
import numpy
from .utils import CTCDecoder


class Recognition:
    def __init__(self, onnx_path, session=None):
        self.session = session
        if self.session is None:
            assert onnx_path is not None
            assert os.path.exists(onnx_path)
            from onnxruntime import InferenceSession
            self.session = InferenceSession(onnx_path,
                                            providers=['CUDAExecutionProvider'])
        self.inputs = self.session.get_inputs()[0]
        self.input_shape = [3, 48, 320]
        self.ctc_decoder = CTCDecoder()

    def resize(self, image, max_wh_ratio):
        input_h, input_w = self.input_shape[1], self.input_shape[2]

        assert self.input_shape[0] == image.shape[2]
        input_w = int((input_h * max_wh_ratio))
        w = self.inputs.shape[3:][0]
        if isinstance(w, str):
            pass
        elif w is not None and w > 0:
            input_w = w
        h, w = image.shape[:2]
        ratio = w / float(h)
        if math.ceil(input_h * ratio) > input_w:
            resized_w = input_w
        else:
            resized_w = int(math.ceil(input_h * ratio))

        resized_image = cv2.resize(image, (resized_w, input_h))
        resized_image = resized_image.transpose((2, 0, 1))
        resized_image = resized_image.astype('float32')
        resized_image = resized_image / 255.0
        resized_image -= 0.5
        resized_image /= 0.5
        padded_image = numpy.zeros((self.input_shape[0], input_h, input_w), dtype=numpy.float32)
        padded_image[:, :, 0:resized_w] = resized_image
        return padded_image

    def __call__(self, images):
        batch_size = 6
        num_images = len(images)

        results = [['', 0.0]] * num_images
        confidences = [['', 0.0]] * num_images
        indices = numpy.argsort(numpy.array([x.shape[1] / x.shape[0] for x in images]))

        for index in range(0, num_images, batch_size):
            input_h, input_w = self.input_shape[1], self.input_shape[2]
            max_wh_ratio = input_w / input_h
            norm_images = []
            for i in range(index, min(num_images, index + batch_size)):
                h, w = images[indices[i]].shape[0:2]
                max_wh_ratio = max(max_wh_ratio, w * 1.0 / h)
            for i in range(index, min(num_images, index + batch_size)):
                norm_image = self.resize(images[indices[i]], max_wh_ratio)
                norm_image = norm_image[numpy.newaxis, :]
                norm_images.append(norm_image)
            norm_images = numpy.concatenate(norm_images)

            outputs = self.session.run(None,
                                       {self.inputs.name: norm_images})
            result, confidence = self.ctc_decoder(outputs[0])
            for i in range(len(result)):
                results[indices[index + i]] = result[i]
                confidences[indices[index + i]] = confidence[i]
        return results, confidences

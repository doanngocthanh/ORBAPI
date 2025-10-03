#!/usr/bin/env python3
"""
Command line interface for PaddleOCR ONNX SDK
"""

import os
import sys
from argparse import ArgumentParser
from warnings import filterwarnings

from .ocr import OCRProcessor

filterwarnings("ignore")


def main():
    """Main CLI entry point"""
    parser = ArgumentParser(description='PaddleOCR ONNX CLI - Text detection and recognition')
    parser.add_argument('input_path', type=str, 
                       help='Path to image file or directory')
    parser.add_argument('-o', '--output', type=str,
                       help='Output directory for annotated images')
    parser.add_argument('--no-draw', action='store_true',
                       help='Do not draw detection boxes and text on output images')
    parser.add_argument('--detection-model', type=str,
                       help='Path to custom detection ONNX model')
    parser.add_argument('--recognition-model', type=str,
                       help='Path to custom recognition ONNX model')
    parser.add_argument('--classification-model', type=str,
                       help='Path to custom classification ONNX model')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose output')

    args = parser.parse_args()

    # Check input path exists
    if not os.path.exists(args.input_path):
        print(f"Error: Input path '{args.input_path}' does not exist")
        sys.exit(1)

    # Initialize OCR processor
    try:
        ocr = OCRProcessor(
            detection_model_path=args.detection_model,
            recognition_model_path=args.recognition_model,
            classification_model_path=args.classification_model
        )
    except Exception as e:
        print(f"Error initializing OCR processor: {e}")
        sys.exit(1)

    # Process input
    draw_results = not args.no_draw
    
    try:
        if os.path.isfile(args.input_path):
            # Process single file
            output_path = None
            if args.output:
                output_filename = f"output_{os.path.basename(args.input_path)}"
                output_path = os.path.join(args.output, output_filename)
                os.makedirs(args.output, exist_ok=True)
            
            results = ocr.process_image(args.input_path, output_path, draw_results)
            
            print(f"Processing: {args.input_path}")
            if results:
                for i, (text, confidence) in enumerate(results):
                    conf_str = f" (confidence: {confidence:.3f})" if args.verbose else ""
                    print(f"  Text {i+1}: {text}{conf_str}")
            else:
                print("  No text detected")
                
            if output_path:
                print(f"  Output saved to: {output_path}")
                
        elif os.path.isdir(args.input_path):
            # Process directory
            results = ocr.process_directory(args.input_path, args.output)
            
            print(f"Processing directory: {args.input_path}")
            print(f"Processed {len(results)} images")
            
            if args.verbose:
                for filename, file_results in results:
                    print(f"\n{filename}:")
                    if file_results:
                        for i, (text, confidence) in enumerate(file_results):
                            print(f"  Text {i+1}: {text} (confidence: {confidence:.3f})")
                    else:
                        print("  No text detected")
        else:
            print(f"Error: '{args.input_path}' is neither a file nor a directory")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error during processing: {e}")
        sys.exit(1)

    print("\nProcessing completed successfully!")


if __name__ == '__main__':
    main()

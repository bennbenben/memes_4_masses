### Import libraries ###
import cv2
import os
import argparse
from collections import defaultdict
import numpy as np
from datetime import datetime

### Helper functions ###
def valid_date(s):
	"""
	Helper function that checks the command line input that execution_date is specified correctly. In this case: %Y-%m-%d
	"""
	try:
		return datetime.strptime(s, "%Y-%m-%d_%H-%M")
	except ValueError:
		err_msg = "not a valid datetime: {0}. Use this format:{1}".format(s,"%Y-%m-%d_%H-%M")
		raise argparse.ArgumentTypeError(err_msg)


### Initialize variables ###
ig_defined_res = (1920, 1080) # IG story max screen resolution. Use height x width as opencv follows numpy orientation
screen_factor = .75 # float
scale_tolerance = 2 # for resizing - only scale
img_vars = defaultdict()


### Application functions ###
def resize_type(file_path: str, defined_res: tuple, screen_factor: float, scale_tolerance: float)->dict:
	"""
	Reads in an image and compares its width with a set of pre-defined resolutions
	Returns a dictionary of 2 key-value pairs: 
	{img_vars['img_obj']: cv2-read image object,
	img_vars['img_res']: (width as float, height as float),
	img_vars['img_aspect_ratio']: float,
	img_vars['defined_res']: (width as float, height float),
	img_vars['screen_factor']: float,
	img_vars['proposed_res']: (width as float, height as float),
	img_vars['proposed_resize_dir']: 'scale' or 'shrink' as string,
	img_vars['scale_tolerance']: float,
	img_vars['proposed_resize_factor']: float,
	img_vars['resize_validity']: boolean (None if proposed_resize_dir='shrink'. True/False if proposed_resize_dir='scale')}
	"""
	# Read image resolutions and aspect ratio, load these variables into img_vars dictionary
	img_vars['img_obj'] = cv2.imread(file_path)
	img_vars['img_res']= img_vars['img_obj'].shape[:2] # returns height, width, channels
	img_vars['img_aspect_ratio'] = float(img_vars['img_res'][1]) / float(img_vars['img_res'][0])
	img_vars['defined_res'] = defined_res
	img_vars['screen_factor'] = screen_factor

	# Propose a resized image resolution (whether its scale or shrink)
	## Scale width and check if height is acceptable
	proposed_width = int(screen_factor * float(img_vars['defined_res'][1])) # 1080 * 0.8 = 864
	proposed_height = int(float(proposed_width) / img_vars['img_aspect_ratio']) # 864 / 0.8 = 1080

	if proposed_height <= defined_res[0]: pass

	## If height is unacceptable, scale height and width will change accordingly
	else:
		proposed_height = int(screen_factor * float(img_vars['defined_res'][0]))
		proposed_width = int(float(proposed_height) * img_vars['img_aspect_ratio'])

	img_vars['proposed_res'] = (proposed_height,proposed_width)

	# Get resize direction: 'scale' or 'shrink' by comparing width (height is also acceptable; but both yield same values)
	if img_vars['proposed_res'][1] <= img_vars['img_res'][1] : img_vars['proposed_resize_dir'] = 'shrink' 
	else: img_vars['proposed_resize_dir'] = 'scale'

	# Check if proposed resize is within specified tolerance
	img_vars['scale_tolerance'] = scale_tolerance
	img_vars['proposed_resize_factor'] = int(float(img_vars['proposed_res'][1]) / float(img_vars['img_res'][1]))

	if img_vars['proposed_resize_dir'] == 'scale':
		if img_vars['proposed_resize_factor'] <= img_vars['scale_tolerance']: img_vars['resize_validity'] = True
		else: img_vars['resize_validity'] = False

	elif img_vars['proposed_resize_dir'] == 'shrink': img_vars['resize_validity'] = None

	return img_vars

def add_pip_vars(img_vars: dict)->dict:
	"""
	Input: takes in output from resize_type function in the form of a dictionary
	Performs: (1) Calculates the Picture-in-Picture (PIP) details, (2) Loads the canvas, (3) Appends the PIP details and canvas object to the dictionary
	Output: outputs the appended dictionary
	"""
	# Read the pre-defined dictionary dimensions and create a canvas of fixed color. Append it to the dictionary
	height, width = img_vars['defined_res']
	# blank_image = np.zeros((height,width,3), dtype=np.uint8) # creates a black image
	colored_image = np.full(shape=(height, width, 3), fill_value=128, dtype=np.uint8) # creates an gray canvas. RGB colour for grey is (128, 128, 128)  
	img_vars['canvas'] = colored_image

	# Get coordinates of resized image on canvas
	y1, x1 = map(int,(np.asarray(img_vars['defined_res']) - np.asarray(img_vars['proposed_res']))/2)
	x2 = x1 + img_vars['proposed_res'][1]
	y2 = y1 + img_vars['proposed_res'][0]

	img_vars['pip_coords'] = {'x1':x1,'x2':x2,'y1':y1,'y2':y2}

	return img_vars

def process_image(img_vars: dict, output_dir: str, exec_datetime: object, iter: int)->dict:
	"""
	Input: (1) Reads the dictionary of image objects and variables, (2) Output file location
	Performs: (1) Image resizing, (2) Pasting resized image into canvas object, (3) Saves the processed image into the output file location
	Output: None
	"""
	# Image resizing
	resized_img = cv2.resize(img_vars['img_obj'], (img_vars['proposed_res'][1], img_vars['proposed_res'][0]))
	print('Checkpoint. Resized image dimensions: height={0}, width={1}, channels={2}'.format(resized_img.shape[0], resized_img.shape[1], resized_img.shape[2]))

	# Make a copy of the canvas and paste the resized image inside
	processed_img = img_vars['canvas']
	print('Checkpoint. New canvas dimensions: height={0}, width={1}, channels={2}'.format(processed_img.shape[0], processed_img.shape[1], processed_img.shape[2]))

	processed_img[img_vars['pip_coords']['y1']:img_vars['pip_coords']['y2'], img_vars['pip_coords']['x1']:img_vars['pip_coords']['x2']]=resized_img

	# Write the processed image to file destination
	exec_date=exec_datetime.strftime("%Y%m%d")
	exec_time=exec_datetime.strftime("%H%M")

	file_dest=os.path.join(output_dir,"{0}_{1}_{2}{3}".format(exec_date,exec_time,str(iter),".jpg"))
	# print(file_dest)
	# file_dest="C:\\Users\\bennb\\Desktop\\formatted_1.jpg"
	cv2.imwrite(file_dest, processed_img)

	return img_vars

### Application Main ###
if __name__=="__main__":

	# Parse arguments
	my_parser = argparse.ArgumentParser(prog="app_transform.py", description="Transform image to an easily readable format by both human and IG story", usage='%(prog)s execution_date(format:%Y-%m-%d_%H-%M) "${meme_absolute_file_paths[@]}" "output_directory"')
	my_parser.add_argument("execution_date", help="execution_date: Input execution datetime as %Y-%m-%d_%H-%M", type=valid_date)
	my_parser.add_argument("meme_absolute_file_paths", help="meme_absolute_file_paths: variable consisting of absolute paths to image files. Use backslash for windows file paths", type=str, nargs="+")
	my_parser.add_argument("output_directory", help="output_directory: file path to output directory", type=str)
	args=my_parser.parse_args()

	print(args)

	# Start Application
	for i in range(len(args.meme_absolute_file_paths)):
		resized_img_vars = resize_type(args.meme_absolute_file_paths[i], ig_defined_res, screen_factor, scale_tolerance)
		pip_img_vars = add_pip_vars(resized_img_vars)
		processed_img_vars = process_image(img_vars=pip_img_vars, output_dir=args.output_directory, exec_datetime=args.execution_date, iter=i)
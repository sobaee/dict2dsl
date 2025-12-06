Install Python >= 3.7 

Install python-lzo, python-idzip

Install my Pyglossaryfork:

https://github.com/sobaee/pyglossaryfork

How:
Put this python script beside the dictionary file and run:
python dict2dsl.py

then follow the interactive instructions.
Dictionary you want to convert should be in .txt or .mtxt extensions, which converted from any other dictionary types using the GREAT Pyglossary.
If you can't manage to use mdict source plugin, then simply convert .txt dictionaries better and serve the same function.

Please feel free for any suggestions and improvements. it made for self using and I shared it for those who may love to continue using the great Goldendict mobile, which proved to be the best multidictionary running app in Android.

N.B: until now the script only identifying idzip path in Termux only; if you don't use Termux, then your .dsl file will not be compressed to dsl.dz and you may need to compress it yourself then. (this is temporary by the way)

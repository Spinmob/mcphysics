call E:\Python\Scripts\activate.bat

:: Clean up previous builds
echo Cleaning dist/ folder...
if exist dist\ rd /s /q dist
mkdir dist

:: Build the package
:: This requires the 'build' package: pip install build
echo.
echo Building McPhysics...
python -m build

:: Upload to PyPI
:: This requires 'twine' and a .pypirc file in your user folder
echo.
echo Uploading to PyPI...
python -m twine upload --skip-existing dist/*

echo.
echo Upload process finished!
pause
# if in windows, please do - choco install ffmpeg 

# Do the below if you have ssl related issues
```
import ssl

# Disable SSL certificate verification (not recommended for production)
ssl._create_default_https_context = ssl._create_unverified_context
```
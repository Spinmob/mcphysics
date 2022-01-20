#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Jack rewrite 2022:
    
    For this to work you need to install opencv python and pyqtgraph, 
    e.g. with the pip command
    
       pip install opencv-python pyqtgraph
    
    Note for pyqtgraph to work, you will need some kind of Qt python library
    installed. For me this came with spyder IDE (also installed by pip). I also
    used spyder to write and test this code, but it worked from just a straight
    python call too.
    
    Currently this will average +/- 10 pixels near the center of the image, as
    indicated by the green + in the image preview. You could turn this
    indicator into a square if you want; just more lines.
    
    It will plot blue, green, red, so versus increasing wavelength. You can
    change this behavior in the p.plot() command.
    
    To calibrate, press "c" while the cross is on something white.
    You need to have the video preview window focused for the keys to be
    noticed. Yes. Janky. I can make a very nice version in a half hour if this 
    is useful.
"""

# import the opencv library
import cv2, pyqtgraph, numpy

# Create the plot window
p = pyqtgraph.PlotWindow()
  
# define a video capture object
vid = cv2.VideoCapture(0)
  
# Calibration multipliers
mb = 1
mg = 1
mr = 1
while(True):
      
    # Capture the video frame
    # by frame
    ret, frame = vid.read()
  
    if ret:
        
        # N1 is height, N2 is width, x is color channels
        N1, N2, x = frame.shape
        
        # Middle
        n1 = int(N1*0.5)
        n2 = int(N2*0.5)
        
        # Draw the + in the middle
        frame[n1-10:n1+10,n2,0]=0    # blue
        frame[n1-10:n1+10,n2,1]=255  # green
        frame[n1-10:n1+10,n2,2]=0    # red
        
        frame[n1,n2-10:n2+10,0]=0    # blue
        frame[n1,n2-10:n2+10,1]=255  # green
        frame[n1,n2-10:n2+10,2]=0    # red
        
        # Show the frame
        cv2.imshow('frame', frame)
        
        # Plot the "spectrum"
        b = mb*numpy.sum(frame[n1-10:n1+10,n2-10:n2+10,0])
        g = mg*numpy.sum(frame[n1-10:n1+10,n2-10:n2+10,1])
        r = mr*numpy.sum(frame[n1-10:n1+10,n2-10:n2+10,2])
        p.plot([1,2,3,4], [b,g,r], stepMode=True, clear=True)
        
      
    # the 'q' button is set as the quit button, or you can close the terminal
    a = cv2.waitKey(20) & 0xFF
    if a == ord('q'):
        break

    # 'c' is for calibrating. Aim it at something white and hit 'c'. 
    # This also auto-scales the y-axis.
    if a == ord('c'):
        mb = mb/b
        mg = mg/g
        mr = mr/r
        print('Calibrating to', mb, mg, mr)
        p.setYRange(-0.05,2.05)
        
  
# After the loop release the cap object
vid.release()
# Destroy all the windows
cv2.destroyAllWindows()
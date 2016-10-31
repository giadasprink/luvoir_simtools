# Import some standard python packages
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from astropy.io import fits, ascii 
from matplotlib import gridspec
from matplotlib import rc
import pdb
import sys
import os 
from astropy.table import Table, Column
mpl.rc('font', family='Times New Roman')
mpl.rcParams['font.size'] = 25.0
import os
from bokeh.io import curdoc
from bokeh.client import push_session

from bokeh.themes import Theme 
import yaml 
from bokeh.plotting import Figure
from bokeh.models import ColumnDataSource, HBox, VBoxForm, HoverTool, Paragraph, Range1d, DataRange1d, Label, DataSource
from bokeh.models.glyphs import Text
from bokeh.layouts import column, row, WidgetBox 
from bokeh.models.widgets import Slider, Panel, Tabs, Div, TextInput, RadioButtonGroup, Select, RadioButtonGroup
from bokeh.io import hplot, vplot, curdoc, output_file, show, vform
from bokeh.models.callbacks import CustomJS
from bokeh.embed import components, autoload_server


import coronagraph as cg  # Import coronagraph model

################################
# PARAMETERS
################################

# Integration time (hours)
Dt = 20.0 # - SLIDER

# Telescopes params
diam = 10. # mirror diameter - SLIDER
Res = 70. # resolution - SLIDER
Tsys = 150. # system temperature - SLIDER

# Planet params
alpha = 90.     # phase angle at quadrature
Phi   = 1.      # phase function at quadrature (already included in SMART run)
Rp    = 1.0     # Earth radii - SLIDER 
r     = 1.0     # semi-major axis (AU) - SLIDER 

# Stellar params
Teff  = 5780.   # Sun-like Teff (K)
Rs    = 1.      # star radius in solar radii

# Planetary system params
d    = 10.     # distance to system (pc)  - SLIDER 
Nez  = 1.      # number of exo-zodis  - SLIDER

# Instrumental Params
owa = 30. #OWA scaling factor - SLIDER
iwa = 2. #IWA scaling factor - SLIDER
De = 1e-4 # dark current - SLIDER
Re = 0.1 # read noise - SLIDER
Dtmax = 1.0 # max single exposure time - SLIDER

# Template
template = ''
global template
global comparison
global Teff
global Ts

################################
# READ-IN DATA
################################

#spec_dict = get_pysynphot_spectra.add_spectrum_to_library() 
#template_to_start_with = 'Earth' 
#spec_dict[template_to_start_with].wave 
#spec_dict[template_to_start_with].flux # <---- these are the variables you need 
#sn = (spec_dict[template_to_start_with].flux * 1.e15 * 36. ) ** 0.5
#junkf = spec_dict[template_to_start_with].flux 
#junkf[spec_dict[template_to_start_with].wave < 1100.] = -999.  
#junkf[spec_dict[template_to_start_with].wave > 1800.] = -999.  
#new_spectrum = ColumnDataSource(data=dict(w=spec_dict[template_to_start_with].wave, f=spec_dict[t#emplate_to_start_with].flux, \
 #                                  w0=spec_dict[template_to_start_with].wave, f0=spec_dict[template_to_start_with].flux, junkf=junkf, sn=sn)) 
#spectrum_template = new_spectrum

# Read-in Earth spectrum file to start 
whichplanet = 'Earth'
if whichplanet == 'Earth':
   fn = 'planets/earth_quadrature_radiance_refl.dat'
   model = np.loadtxt(fn, skiprows=8)
   lamhr = model[:,0]
   radhr = model[:,1]
   solhr = model[:,2]
# Calculate hi-resolution reflectivity
   Ahr   = np.pi*(np.pi*radhr/solhr)
   lammin = min(lamhr)
   lammax = max(lamhr)
   planet_label = ['Synthetic spectrum generated by T. Robinson (Robinson et al. 2011)']



Ahr_ = Ahr
lamhr_ = lamhr
solhr_ = solhr
Teff_ = Teff
Rs_ = Rs


################################
# RUN CORONAGRAPH MODEL
################################

# Run coronagraph with default LUVOIR telescope (aka no keyword arguments)
lam, dlam, A, q, Cratio, cp, csp, cz, cez, cD, cR, cth, DtSNR = \
    cg.count_rates(Ahr, lamhr, alpha, Phi, Rp, Teff, Rs, r, d, Nez, diam, Res, Tsys, iwa, owa,solhr=solhr, De=De, Re=Re, Dtmax=Dtmax)
# Calculate background photon count rates
cb = (cz + cez + csp + cD + cR + cth)
# Convert hours to seconds
Dts = Dt * 3600.
# Calculate signal-to-noise assuming background subtraction (the "2")
SNR  = cp*Dts/np.sqrt((cp + 2*cb)*Dts)
# Calculate 1-sigma errors
sig= Cratio/SNR
# Add gaussian noise to flux ratio
spec = Cratio + np.random.randn(len(Cratio))*sig

lastlam = lam
lastCratio = Cratio
snr_ymax = np.max(Cratio)*1e9
yrange=[snr_ymax]
planet = ColumnDataSource(data=dict(lam=lam, cratio=Cratio*1e9, spec=spec*1e9, downerr=(spec-sig)*1e9, uperr=(spec+sig)*1e9))
plotyrange = ColumnDataSource(data = dict(yrange=yrange))
lamC = lastlam * 0.
CratioC = lastCratio * 0.
global lamC
global CratioC
global snr_plot
compare = ColumnDataSource(data=dict(lam=lamC, cratio=Cratio*1e9)) #test
textlabel = ColumnDataSource(data=dict(label = planet_label))


################################
# BOKEH PLOTTING
################################

#fixed y axis is bad
snr_ymax = np.max(Cratio)*1e9
snr_plot = Figure(plot_height=500, plot_width=750, 
              tools="crosshair,pan,reset,resize,save,box_zoom,wheel_zoom",
              toolbar_location='right')
#snr_plot.rect(x=[0.2, 3.5], y=[-0.2, snr_ymax+0.1])
snr_plot.x_range = Range1d(0.2, 3., bounds=(0.2, 5))
snr_plot.y_range = DataRange1d(start = -0.2, end=1.5)
#snr_plot.y_range.start = -0.2
#snr_plot.y_range.end = snr_ymax
#cursession().store_objects(snr_plot)
snr_plot.background_fill_color = "beige"
snr_plot.background_fill_alpha = 0.5
snr_plot.yaxis.axis_label='F_p/F_s (x10^9)' 
snr_plot.xaxis.axis_label='Wavelength [micron]'
snr_plot.title.text = 'Planet Spectrum'


snr_plot.line('lam','cratio',source=compare,line_width=2.0, color="gray", alpha=0.7)
snr_plot.line('lam','cratio',source=planet,line_width=2.0, color="green", alpha=0.7)
snr_plot.circle('lam', 'spec', source=planet, fill_color='red', line_color='black', size=8) 
snr_plot.segment('lam', 'downerr', 'lam', 'uperr', source=planet, line_width=1, line_color='grey', line_alpha=0.5) 

#rectangle behind annotation:
snr_plot.quad(top = [-0.1], left=[0.2], right=[3.5], bottom=[-0.2], color="white")

glyph = Text(x=0.25, y=-0.19, text="label", text_font_size='9pt')
snr_plot.add_glyph(textlabel, glyph)

show(snr_plot) 

def change_filename(attrname, old, new): 
   format_button_group.active = None 


instruction0 = Div(text="""Specify a filename here:
                           (no special characters):""", width=300, height=15)
text_input = TextInput(value="filename", title=" ", width=100)
instruction1 = Div(text="""Then choose a file format here:""", width=300, height=15)
format_button_group = RadioButtonGroup(labels=["txt", "fits"])
instruction2 = Div(text="""The link to download your file will appear here:""", width=300, height=15)
link_box  = Div(text=""" """, width=300, height=15)


def i_clicked_a_button(new): 
    filename=text_input.value + {0:'.txt', 1:'.fits'}[format_button_group.active]
    print "Your format is   ", format_button_group.active, {0:'txt', 1:'fits'}[format_button_group.active] 
    print "Your filename is: ", filename 
    fileformat={0:'txt', 1:'fits'}[format_button_group.active]
    link_box.text = """Working""" 
 
    t = Table(planet.data)
    t = t['lam', 'spec','cratio','uperr','downerr'] 

    if (format_button_group.active == 1): t.write(filename, overwrite=True) 
    if (format_button_group.active == 0): ascii.write(t, filename)
 
    os.system('gzip -f ' +filename) 
    os.system('cp -rp '+filename+'.gz /home/jtastro/jt-astro.science/outputs') 
    print    """Your file is <a href='http://jt-astro.science/outputs/"""+filename+""".gz'>"""+filename+""".gz</a>. """

    link_box.text = """Your file is <a href='http://jt-astro.science/outputs/"""+filename+""".gz'>"""+filename+""".gz</a>. """


  

def update_data(attrname, old, new):
   #how do I make it so that it will update the spectrum file here but only if it CHANGES?
    print 'Updating model for exptime = ', exptime.value, ' for planet with R = ', radius.value, ' at distance ', distance.value, ' parsec '
    print '                   exozodi = ', exozodi.value, 'diameter (m) = ', diameter.value, 'resolution = ', resolution.value
    print '                   temperature (K) = ', temperature.value, 'IWA = ', inner.value, 'OWA = ', outer.value
    print 'You have chosen planet spectrum: ', template.value
    print 'You have chosen comparison spectrum: ', comparison.value
    try:
       lasttemplate
    except NameError:
       lasttemplate = 'Earth' #default first spectrum
    try:
       lastcomparison
    except NameError:
       lastcomparison = 'none' #default first spectrum
    global lasttemplate
    global Ahr_
    global lamhr_
    global solhr_
    global Teff_
    global Rs_
    global Ahr_c
    global lamhr_c
    global solhr_c
    global Teff_c
    global Rs_c
    global radius_c
    global semimajor_c
    global lastcomparison
    
# Read-in new spectrum file only if changed
#'BBody' variable some of these have in place of solhr is
# because not all of these read in a stellar spectrum from their files
# so the coronagraph model can use a blackbody instead (note: update so that
# it's self-consistently done for stellar types once we get planets around other
# stars if that becomes important, which I think it will)
    if template.value != lasttemplate:
       if template.value == 'Earth':
          fn = 'planets/earth_quadrature_radiance_refl.dat'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_ = model[:,0]
          radhr = model[:,1]
          solhr_ = model[:,2]
          Ahr_   = np.pi*(np.pi*radhr/solhr_)
          semimajor.value = 1.
          radius.value = 1.
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by T. Robinson (Robinson et al. 2011)']


       if template.value == 'Venus':
          fn = 'planets/Venus_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = model[:,2]
          semimajor.value = 0.72
          radius.value = 0.94
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by T. Robinson']


       if template.value =='Archean Earth':
          fn = 'planets/ArcheanEarth_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = model[:,2]
          semimajor.value = 1.
          radius.value = 1.
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by G. Arney (Arney et al. 2016)']
          
       if template.value =='Hazy Archean Earth':
          fn = 'planets/Hazy_ArcheanEarth_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = model[:,2]
          semimajor.value = 1.
          radius.value = 1.
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by G. Arney (Arney et al. 2016)']


       if template.value =='1% PAL O2 Proterozoic Earth':
          fn = 'planets/proterozoic_hi_o2_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = "BBody"
          semimajor.value = 1.
          radius.value = 1.
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by G. Arney (Arney et al. 2016)']
          

       if template.value =='0.1% PAL O2 Proterozoic Earth':
          fn = 'planets/proterozoic_low_o2_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = "BBody"
          semimajor.value = 1.
          radius.value = 1.
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by G. Arney (Arney et al. 2016)']

          
       if template.value =='Early Mars':
          fn = 'planets/EarlyMars_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = model[:,2]
          semimajor.value = 1.52
          radius.value = 0.53
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by G. Arney based on Smith et al. 2014']

          
       if template.value =='Mars':
          fn = 'planets/Mars_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = 'Bbody'
          semimajor.value = 1.52
          radius.value = 0.53         
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by T. Robinson']

          
       if template.value =='Jupiter':
          fn = 'planets/Jupiter_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = 'Bbody'
          semimajor.value = 5.46
          radius.value = 10.97
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['0.9-0.3 microns observed by Karkoschka et al. (1998); 0.9-2.4 microns observed by Rayner et al. (2009)']

          
       if template.value =='Saturn':
          fn = 'planets/Saturn_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = 'Bbody'
          semimajor.value = 9.55
          radius.value = 9.14
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['0.9-0.3 microns observed by Karkoschka et al. (1998); 0.9-2.4 microns observed by Rayner et al. (2009)']

          
       if template.value =='Uranus':
          fn = 'planets/Uranus_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = 'Bbody'
          semimajor.value = 19.21
          radius.value = 3.98
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['0.9-0.3 microns observed by Karkoschka et al. (1998); 0.9-2.4 microns observed by Rayner et al. (2009)']

          
       if template.value =='Neptune':
          fn = 'planets/Neptune_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = 'Bbody'
          semimajor.value = 29.8
          radius.value = 3.86
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['0.9-0.3 microns observed by Karkoschka et al. (1998); 0.9-2.4 microns observed by Rayner et al. (2009)']

       if template.value =='Warm Neptune at 2 AU':
          fn = 'planets/Reflection_a2_m1.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          lamhr_ = lamhr_ / 1000. #convert to microns
          Ahr_ = Ahr_ * 0.67 #convert to geometric albedo
          solhr_ = 'Bbody'
          semimajor.value = 2.0
          radius.value = 3.86
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by R. Hu (Hu and Seager 2014)']

       if template.value =='Warm Neptune w/o Clouds at 1 AU':
          fn = 'planets/Reflection_a1_m2.6_LM_NoCloud.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          lamhr_ = lamhr_ / 1000. #convert to microns
          Ahr_ = Ahr_ * 0.67 #convert to geometric albedo
          solhr_ = 'Bbody'
          semimajor.value = 1.0
          radius.value = 3.86
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by R. Hu (Hu and Seager 2014)']
          
       if template.value =='Warm Neptune w/ Clouds at 1 AU':
          fn = 'planets/Reflection_a1_m2.6_LM.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          lamhr_ = lamhr_ / 1000. #convert to microns
          Ahr_ = Ahr_ * 0.67 #convert to geometric albedo
          solhr_ = 'Bbody'
          semimajor.value = 1.0
          radius.value = 3.86
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by R. Hu']

       if template.value =='Warm Jupiter at 0.8 AU':
          fn = 'planets/0.8AU_3x.txt'
          model = np.loadtxt(fn, skiprows=1)
          lamhr_ = model[:,1]
          Ahr_ = model[:,3]
          solhr_ = 'Bbody'
          semimajor.value = 0.8
          radius.value = 10.97
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by K. Cahoy (Cahoy et al. 2010)']

       if template.value =='Warm Jupiter at 2 AU':
          fn = 'planets/2AU_3x.txt'
          model = np.loadtxt(fn, skiprows=1)
          lamhr_ = model[:,1]
          Ahr_ = model[:,3]
          solhr_ = 'Bbody'
          semimajor.value = 2.0
          radius.value = 10.97
          Teff_  = 5780.   # Sun-like Teff (K)
          Rs_    = 1.      # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by K. Cahoy (Cahoy et al. 2010)']             
          
       if template.value =='False O2 Planet (F2V star)':
          fn = 'planets/fstarcloudy_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_ = model[:,0]
          Ahr_ = model[:,1]
          solhr_ = "Bbody"
          semimajor.value = 1.72 #Earth equivalent distance for F star
          radius.value = 1.
          Teff_  = 7050.   # F2V Teff (K)
          Rs_    = 1.3     # star radius in solar radii
          planet_label = ['Synthetic spectrum generated by S. Domagal-Goldman (Domagal-Goldman et al. 2014)']
  
          
       global lammin
       global lammax
       global planet_label
       lammin=min(lamhr_)
       lammax=max(lamhr_)-0.2 #this fixes a weird edge issue
          
          
   # if template.value == lasttemplate:
   #    Ahr_ = Ahr
   #    lamhr_ = lamhr
   #    solhr_ = solhr
       #semimajor_ = semimajor.value
       #radius_ = radius.value

    print "ground based = ", ground_based.value
    if ground_based.value == "No":
       ground_based_ = False
    if ground_based.value == "Yes":
       ground_based_ = True

    if ground_based_ == True:
       lammin=min(lamhr_)+0.05 #edge issues worse when ground based turned on 
       lammax=max(lamhr_)-0.25 
    
    # Run coronagraph 
    lam, dlam, A, q, Cratio, cp, csp, cz, cez, cD, cR, cth, DtSNR = \
        cg.count_rates(Ahr_, lamhr_, alpha, Phi, radius.value, Teff_, Rs_, semimajor.value, distance.value, exozodi.value, diameter.value, resolution.value, temperature.value, inner.value, outer.value,  solhr=solhr_, lammin=lammin, lammax=lammax, De=darkcurrent.value, Re=readnoise.value, Dtmax = dtmax.value, GROUND=ground_based_)


    # Calculate background photon count rates
    cb = (cz + cez + csp + cD + cR + cth)
    # Convert hours to seconds
    Dts = exptime.value * 3600.
    # Calculate signal-to-noise assuming background subtraction (the "2")
    SNR  = cp*Dts/np.sqrt((cp + 2*cb)*Dts)
    # Calculate 1-sigma errors
    sig= Cratio/SNR
    # Add gaussian noise to flux ratio
    spec = Cratio + np.random.randn(len(Cratio))*sig
    lastlam = lam
    lastCratio = Cratio
    global lastlam
    global lastCratio
    planet.data = dict(lam=lam, cratio=Cratio*1e9, spec=spec*1e9, downerr=(spec-sig)*1e9, uperr=(spec+sig)*1e9)
    textlabel.data = dict(label=planet_label)

    format_button_group.active = None
    lasttemplate = template.value
    snr_ymax_ = np.max(Cratio)*1e9
    global snr_ymax_
    yrange=[snr_ymax]
    plotyrange.data = dict(yrange=yrange)
   # snr_plot.y_range = DataRange1d(start = -0.2, end=snr_ymax_)
    global snr_plot

    if comparison.value != lastcomparison:
      if comparison.value == 'Earth':
          fn = 'planets/earth_quadrature_radiance_refl.dat'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_c = model[:,0]
          radhr_c = model[:,1]
          solhr_c = model[:,2]
          Ahr_c   = np.pi*(np.pi*radhr_c/solhr_c)
          semimajor_c = 1.
          radius_c = 1.
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by T. Robinson (Robinson et al. 2011)']

      if comparison.value == 'Venus':
          fn = 'planets/Venus_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = model[:,2]
          semimajor_c = 0.72
          radius_c = 0.94
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by T. Robinson']


      if comparison.value =='Archean Earth':
          fn = 'planets/ArcheanEarth_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = model[:,2]
          semimajor_c = 1.
          radius_c = 1.
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by G. Arney (Arney et al. 2016)']
          
      if comparison.value =='Hazy Archean Earth':
          fn = 'planets/Hazy_ArcheanEarth_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = model[:,2]
          semimajor_c = 1.
          radius_c = 1.
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by G. Arney (Arney et al. 2016)']


      if comparison.value =='1% PAL O2 Proterozoic Earth':
          fn = 'planets/proterozoic_hi_o2_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = "BBody"
          semimajor_c = 1.
          radius_c = 1.
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by G. Arney (Arney et al. 2016)']
          

      if comparison.value =='0.1% PAL O2 Proterozoic Earth':
          fn = 'planets/proterozoic_low_o2_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = "BBody"
          semimajor_c = 1.
          radius_c = 1.
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by G. Arney (Arney et al. 2016)']

          
      if comparison.value =='Early Mars':
          fn = 'planets/EarlyMars_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = model[:,2]
          semimajor_c = 1.52
          radius_c = 0.53
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by G. Arney based on Smith et al. 2014']

          
      if comparison.value =='Mars':
          fn = 'planets/Mars_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=8)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = 'Bbody'
          semimajor_c = 1.52
          radius_c = 0.53         
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by T. Robinson']

          
      if comparison.value =='Jupiter':
          fn = 'planets/Jupiter_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = 'Bbody'
          semimajor_c = 5.46
          radius_c = 10.97
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['0.9-0.3 microns observed by Karkoschka et al. (1998); 0.9-2.4 microns observed by Rayner et al. (2009)']

          
      if comparison.value =='Saturn':
          fn = 'planets/Saturn_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = 'Bbody'
          semimajor_c = 9.55
          radius_c = 9.14
          Teff_c = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['0.9-0.3 microns observed by Karkoschka et al. (1998); 0.9-2.4 microns observed by Rayner et al. (2009)']

          
      if comparison.value =='Uranus':
          fn = 'planets/Uranus_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = 'Bbody'
          semimajor_c = 19.21
          radius_c = 3.98
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['0.9-0.3 microns observed by Karkoschka et al. (1998); 0.9-2.4 microns observed by Rayner et al. (2009)']

          
      if comparison.value =='Neptune':
          fn = 'planets/Neptune_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = 'Bbody'
          semimajor_c = 29.8
          radius_c = 3.86
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['0.9-0.3 microns observed by Karkoschka et al. (1998); 0.9-2.4 microns observed by Rayner et al. (2009)']


      if comparison.value =='Warm Neptune at 2 AU':
          fn = 'planets/Reflection_a2_m1.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          lamhr_c = lamhr_c / 1000. #convert to microns
          Ahr_c = Ahr_c * 0.67 #convert to geometric albedo
          solhr_c = 'Bbody'
          semimajor_c = 1.0
          radius_c = 3.86
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by R. Hu (Hu and Seager 2014)']

      if comparison.value =='Warm Neptune w/o Clouds at 1 AU':
          fn = 'planets/Reflection_a1_m2.6_LM_NoCloud.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          lamhr_c = lamhr_c / 1000. #convert to microns
          Ahr_c = Ahr_c* 0.67 #convert to geometric albedo
          solhr_c = 'Bbody'
          semimajor_c = 1.0
          radius_c = 3.86
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by R. Hu (Hu and Seager 2014)']
          
      if comparison.value =='Warm Neptune w/ Clouds at 1 AU':
          fn = 'planets/Reflection_a1_m2.6_LM.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          lamhr_c = lamhr_c / 1000. #convert to microns
          Ahr_c = Ahr_c * 0.67 #convert to geometric albedo
          solhr_c = 'Bbody'
          semimajor_c = 2.0
          radius_c = 3.86
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by R. Hu']

      if comparison.value =='Warm Jupiter at 0.8 AU':
          fn = 'planets/0.8AU_3x.txt'
          model = np.loadtxt(fn, skiprows=1)
          lamhr_c = model[:,1]
          Ahr_c = model[:,3]
          solhr_c = 'Bbody'
          semimajor_c = 0.8
          radius_c = 10.97
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by K. Cahoy (Cahoy et al. 2010)']

      if comparison.value =='Warm Jupiter at 2 AU':
          fn = 'planets/2AU_3x.txt'
          model = np.loadtxt(fn, skiprows=1)
          lamhr_c = model[:,1]
          Ahr_c = model[:,3]
          solhr_c = 'Bbody'
          semimajor_c = 2.0
          radius_c = 10.97
          Teff_c  = 5780.   # Sun-like Teff (K)
          Rs_c    = 1.      # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by K. Cahoy (Cahoy et al. 2010)']              

      if comparison.value =='False O2 Planet (F2V star)':
          fn = 'planets/fstarcloudy_geo_albedo.txt'
          model = np.loadtxt(fn, skiprows=0)
          lamhr_c = model[:,0]
          Ahr_c = model[:,1]
          solhr_c = "Bbody"
          semimajor_c = 1.72 #Earth equivalent distance for F star
          radius_c = 1.
          Teff_c  = 7050.   # F2V Teff (K)
          Rs_c    = 1.3     # star radius in solar radii
          planet_label_c = ['Synthetic spectrum generated by S. Domagal-Goldman (Domagal-Goldman et al. 2014)']          

      global lammin_c
      global lammax_c
      lammin_c=min(lamhr_c)
      lammax_c=max(lamhr_c)-0.2 #this fixes a weird edge issue

              

    if comparison.value != 'none':
      print 'comparison.value =', comparison.value
      print  'running comparison spectrum'
      lamC, dlamC, AC, qC, CratioC, cpC, cspC, czC, cezC, cDC, cRC, cthC, DtSNRC = \
       cg.count_rates(Ahr_c, lamhr_c, alpha, Phi, radius_c, Teff_c, Rs_c, semimajor_c, distance.value, exozodi.value, diameter.value, resolution.value, temperature.value, inner.value, outer.value,  solhr=solhr_c, lammin=lammin_c, lammax=lammax_c, De=darkcurrent.value, Re=readnoise.value, Dtmax = dtmax.value)
      print 'ran comparison coronagraph noise model'

    if comparison.value == 'none':
        lamC = lamhr_ * 0.
        CratioC = Ahr_ * 0.
     
 
    lastcomparison = comparison.value
    print "constructing compare.data"
    #print lamC
    #print CratioC
    compare.data = dict(lam=lamC, cratio=CratioC*1e9)

    

       
######################################
# SET UP ALL THE WIDGETS AND CALLBACKS 
######################################

source = ColumnDataSource(data=dict(value=[]))
source.on_change('data', update_data)
exptime  = Slider(title="Integration Time (hours)", value=20., start=1., end=300.0, step=1.0, callback_policy='mouseup')
exptime.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
distance = Slider(title="Distance (parsec)", value=10., start=1.28, end=50.0, step=0.2, callback_policy='mouseup') 
distance.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
radius   = Slider(title="Planet Radius (R_Earth)", value=1.0, start=0.5, end=20., step=0.1, callback_policy='mouseup') 
radius.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
semimajor= Slider(title="Semi-major axis of orbit (AU)", value=1.0, start=0.1, end=20., step=0.1, callback_policy='mouseup') 
semimajor.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
exozodi  = Slider(title="Number of Exozodi", value = 1.0, start=1.0, end=10., step=1., callback_policy='mouseup') 
exozodi.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
diameter  = Slider(title="Mirror Diameter (meters)", value = 10.0, start=1.0, end=50., step=1., callback_policy='mouseup') 
diameter.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
resolution  = Slider(title="Telescope Resolution (R)", value = 70.0, start=10.0, end=200., step=5., callback_policy='mouseup') 
resolution.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
temperature  = Slider(title="Telescope Temperature (K)", value = 150.0, start=90.0, end=400., step=10., callback_policy='mouseup') 
temperature.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
inner  = Slider(title="Inner Working Angle factor x lambda/D", value = 2.0, start=1.22, end=4., step=0.2, callback_policy='mouseup') 
inner.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
outer  = Slider(title="Outer Working Angle factor x lambda/D", value = 30.0, start=20, end=100., step=1, callback_policy='mouseup') 
outer.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
darkcurrent  = Slider(title="Dark current (counts/s)", value = 1e-4, start=1e-5, end=1e-3, step=1e-5, callback_policy='mouseup') 
darkcurrent.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
readnoise  = Slider(title="Read noise (counts/pixel)", value = 0.1, start=0.01, end=1, step=0.05, callback_policy='mouseup') 
readnoise.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
dtmax  = Slider(title="Maximum single exposure time (hours)", value = 1, start=0.1, end=10., step=0.5, callback_policy='mouseup') 
dtmax.callback = CustomJS(args=dict(source=source), code="""
    source.data = { value: [cb_obj.value] }
""")
#ground based choice
#ground_based = RadioButtonGroup(name="Simulate ground based observing?", labels=["False", "True"], active=0)
ground_based = Select(title="Simulate ground-based observation?", value="No", options=["No",  "Yes"])

#select menu for planet
template = Select(title="Planet Spectrum", value="Earth", options=["Earth",  "Archean Earth", "Hazy Archean Earth", "1% PAL O2 Proterozoic Earth", "0.1% PAL O2 Proterozoic Earth","Venus", "Early Mars", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune",'----','Warm Neptune at 2 AU', 'Warm Neptune w/o Clouds at 1 AU', 'Warm Neptune w/ Clouds at 1 AU','Warm Jupiter at 0.8 AU', 'Warm Jupiter at 2 AU',"False O2 Planet (F2V star)"])
#select menu for comparison spectrum
comparison = Select(title="Show comparison spectrum?", value ="none", options=["none", "Earth",  "Archean Earth", "Hazy Archean Earth", "1% PAL O2 Proterozoic Earth", "0.1% PAL O2 Proterozoic Earth","Venus", "Early Mars", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune",'----','Warm Neptune at 2 AU', 'Warm Neptune w/o Clouds at 1 AU', 'Warm Neptune w/ Clouds at 1 AU','Warm Jupiter at 0.8 AU', 'Warm Jupiter at 2 AU', "False O2 Planet (F2V star)"])


oo = column(children=[exptime, diameter, resolution, temperature, ground_based]) 
pp = column(children=[template, comparison, distance, radius, semimajor, exozodi]) 
qq = column(children=[instruction0, text_input, instruction1, format_button_group, instruction2, link_box])
ii = column(children=[inner, outer, darkcurrent, readnoise, dtmax])

observation_tab = Panel(child=oo, title='Observation')
planet_tab = Panel(child=pp, title='Planet')
instrument_tab = Panel(child=ii, title='Instrumentation')
download_tab = Panel(child=qq, title='Download')

for w in [text_input]: 
    w.on_change('value', change_filename)
format_button_group.on_click(i_clicked_a_button)

#gna - added this
for ww in [template]: 
    ww.on_change('value', update_data)

for www in [comparison]: 
    www.on_change('value', update_data)

for gg in [ground_based]: 
    gg.on_change('value', update_data)

inputs = Tabs(tabs=[ planet_tab, observation_tab, instrument_tab, download_tab ])
curdoc().add_root(row(children=[inputs, snr_plot])) 

#curdoc().theme = Theme(json=yaml.load("""
#attrs:
#    Figure:
#        background_fill_color: '#2F2F2F'
#        border_fill_color: '#2F2F2F'
#        outline_line_color: '#444444'
#    Axis:
#        axis_line_color: "white"
#        axis_label_text_color: "white"
#        major_label_text_color: "green"
#        major_tick_line_color: "white"
#        minor_tick_line_color: "white"
#        minor_tick_line_color: "white"
#    Grid:
#        grid_line_dash: [6, 4]
#        grid_line_alpha: .9
#    Title:
#        text_color: "green"
#""")) 


curdoc().add_root(source) 

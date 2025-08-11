UK AIRSPACE DATA SET
====================

DATA FILE - OUT_UK_Airspace.zip
VALIDITY  - 28 Nov 2010

UK Outline data set for the Kinetic SBS BaseStation software.

---------------------------------------------------------
Please read these instuctions carefully before installing
---------------------------------------------------------

****IMPORTANT NOTE FOR EXISTING UK DATA USERS****

--THIS RELEASE IS NOT COMPATIBLE WITH EARLIER DATA SETS--

WITH CURRENT DEVELOPMENT OF ADDITIONAL COUNTRY SETS THE EARLIER FILE NAMING CONVENTION WAS FOUND UNWORKABLE. IT HAS THEREFORE BEEN NECESSARY TO DEVELOP A NEW FILE NAMING SYSTEM - THE RESULT OF WHICH ALL OUTLINE AND WAYPOINT FILENAMES HAVE CHANGED IN THIS RELEASE.

EXISTING USERS SHOULD READ THE INSTALLATION SECTION FOR FURTHER DETAILS.



CONTENTS
========

This zip contains the current UK AIP (Air Pilot) information converted for use with the Kinetic BaseStation software. 

The information is extremely comprehensive and includes: 

1. Final approach centrelines for 115 airfields. (10nm for precision approach runways and 6nm for non precision approaches).
2. Upper and Lower airways centrelines.
3. UK Lower Airway edges (less visually complex than centrelines).
4. Airfield ATZ's and MATZ's (Aerodrome Traffic Zones).
5. Control Area, TMA and Control Zone outlines.
6. Danger, Restricted and Prohibited Areas.
7. FIR boundaries and ATSDA airspace.
8. Military airspace including AIAA, AARA, ATA, MTA, TRA, ARA and E3D Orbit areas.
9. VOR roses.

There is a huge amount of information in these files. Although BaseStation will happily run with all loaded and active it need not be said that you can end up with a very cluttered display. It would be wiser for users to be selective about the files they wish to have active on their systems. Most files are logically marked so it should not be too difficult to disable those not needed.


DATA STRUCTURE
============== 

A full list of the file types supplied is as follows. 

With this release the naming convention has been changed to include the ICAO country prefix. For the UK files the names have been changed to the following:

Prefix    Type                     Description
------    ----                     -----------

UK_AFP	  Airfield_Plans           High resolution/low detail airfield diagrams. Now a separate download. 

UK_FA	  Final_Approach_Tracks    These runway centrelines run to 10nm for precision approach runways 
UK_FA20                           and to 6nm for non precision approaches. Optional 20nm
                                   centrelines (FA20 files) are available for some airfields.
                                   Range marks are at 1nm intervals with deeper indents every 5nm.

UK_AWY_L  Airways_Lower_CL         A single file providing all Lower Airway centrelines.

UK_AWY_U  Airways_Upper_CL         A single file providing all Upper Airway centrelines.

UK_ATZ    Aerodrome Traffic Zones  Files for ATZ (separate civil and mil files) and MATZ airspace.
UK_ATZ_M
UK_MIL_MATZ	

UK_CTA    Control Areas            Control Area (CTA) and Terminal Control Area (TMA) airspace files. 
UK_TMA                             Includes a lower airways boundary file (less clutter than using centrelines). 

UK_CTR    Control Zones            Control Zone files.

UK_DA     Danger Areas             All Danger Areas greater than 2nm radius are included. Separate files show 
                                   Prohibited and Restricted Areas.

UK_FIR    FIR                      Files provide FIR, ATSDA and HUACA_CTA airspace.

UK_LARS   Lower Airspace Radar     Files provide Lower Airspace Radar services areas of coverage.
          Service

UK_MIL    Mil                      Military AIAA, MTA, RTA, AARA, ATA, E3D and ARA areas.

UK_VOR    VOR Roses              VOR roses for all UK VORs.



COAST_    Revised UK and Ireland coastlines are available as a separate download.


Areas Descriptions

AIAA 	Area of Intense Aerial Activity
AARA 	Air to Air Refuelling Area
ARA 	Advisory Radio Area
ATA	Aerial Tactics Area
MTA     Military Training Area
TRA     Temporary Reserved Area
E3AOA	E3A Orbit Area
FIR	FIR Boundary (GL - FL245)
UIR	UIR Boundary (FL245 - FL660)
ATSDA	ATS Delegated Area
HUACA	Highlands Upper Area Control Area


============
INSTALLATION
============

Read through the whole of this section first before returning here to install the files.  Installation is a little complex as there are choices to be made as to which files you may wish to use.

I suggest you unzip this ZIP file to a temporary folder on your PC before moving files to your BaseStation folder.

After unzipping you should have: 

235 outline files in the Temp folder. 
A VATSIM sub folder with 45 holding patterns.

Existing users section (ignore if installing for the first time)
----------------------------------------------------------------

All the files included in this zip have a time stamp of 01/12/2010 00:00. This should allow for the checking and removal of any older files.

Because filenames have changed it is essential that you remove all my older outline files from BaseStation. Don't delete the whole content as you may have some SBS-R files or SBSPlotter files present. You just need to remove files with the following prefixes:

ATZ_ 
AWY_
CTA_
CTR_
DA_
FA20_
FA_
HOLD_
FIR_
LARS_
MIL_
TMA_
VOR_

If you have any files from Jetvision (Andy's worldwide sets) I can't suggest an easy way to keep these. It may be best to run a complete reinstall of his data too as his files are also updated from time to time.




Moving the files
----------------

1. Close BaseStation down.

2. Copy ALL the .OUT files into your Kinetic Outlines folder. 

3. If you find the VATSIM holds useful also copy the 98 files in this sub folder to your Kinetic Outlines folder.


Setting up BaseStation
----------------------

4. Go to the BaseStation Display Settings, Data Files menu option. Here you will see all installed Outline files - and they will initially default to ON (ticked). Decide which files you do not want active and untick them. For example if you live in Kent it isn't really necessary to have BaseStation load the airfield plans for Sumburgh (UK_AFP_Sumburgh_EGPB.out), Kirkwall (UK_AFP_Kirkwall_EGPA.out) or other northerly stations.

5. In this list you will also find both 10nm and 20nm centrelines for Heathrow, Gatwick, Stansted and Luton active. CHOOSE THE SET YOU PREFER and untick the other files. The choice is between:

UK_FA_EGLL and UK_FA20_EGLL (Heathrow)
UK_FA_EGKK and UK_FA20_EGKK (Gatwick)
UK_FA_EGSS and UK_FA20_EGSS (Stansted)
UK_FA_EGGW and UK_FA20_EGGW (Luton)

5. Go to the Display Settings, Outlines menu to activate or deactivate each of the 30 Outline sections as required. To label the outline sections correctly see the Display Settings section below.

If you are unsure about what to do then read through the instructions again so you are clear as to how to proceed. If in doubt don't do anything. Either drop me an email or post a question on the Kinetic forum.

*****WARNING*****

Sorry to add yet another one but..

SBS_Resources also contains airspace file sets but these are older data. If you get SBS-R do not install outlines from this utility - except for Paul's high resolution airfield plans (AFP files). If you install other outlines you will end up with duplicate files on your system.




DISPLAY SETTINGS
================

Changing the BaseStation field names
------------------------------------

The default BaseStation Outline titles do not show all the airspace types I have provided here - but these can be added.

To change the values I assume that users are familiar with Notepad and with altering information in INI files. Before making these changes I recommend making a backup of the BaseStation.INI file.

1. Open the BaseStation.INI file. 

2. Scroll down the page until you come to a section that begins with [DrawingSettings]

3. Add the following lines to this section:

OutlineTypes-5=Final Apr
OutlineTypes-6=Lwr Awy C/L
OutlineTypes-7=Upr Awy C/L
OutlineTypes-8=ATZ
OutlineTypes-9=CTA/TMA
OutlineTypes-10=CTR
OutlineTypes-11=Danger Area
OutlineTypes-12=FIR
OutlineTypes-13=TACAN Rte
OutlineTypes-14=Field 14
OutlineTypes-15=VOR Roses
OutlineTypes-16=Field 16
OutlineTypes-17=LARS
OutlineTypes-18=MATZ
OutlineTypes-19=Lwr Awy Bdy
OutlineTypes-20=AARA
OutlineTypes-21=AIAA
OutlineTypes-22=MTA
OutlineTypes-23=ATA
OutlineTypes-24=ATSDA





Comments
========
SID, STAR, IAP's and Hold procedures are not included in this data set. These are procedures rather than airspace boundaries and as such they are outside the scope of this work. Such procedures change often and would require frequent updating to remain current. 

I have included some old VATSIM holding pattern files for those who like the Holds in Basestation but I won't be keeping these up to date.


Credits
-------
Full credit must go to the Kintic software team for providing such excellent software. 

Thanks must also go to Sean Johnson (Sejo) who kicked this airspace idea off in the first place with his conversion of the VATSIM data. Without his initial effort I would never have looked at further development.

Thanks also go to Leland Vandervort (P28R) for his help and advice with this work. It is but a small fraction of his total contribution to SBS users. Thanks also to Dave Reid who has also provided much in the way of help and support to all of us.

Have fun..

John Woodside
bones@mcb.net
400CB6
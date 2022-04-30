import json
import sys
import smtplib
import os

from senec import Senec
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

#read config.json
with open('config.json') as config_file:
  config = json.load(config_file)

#init api
api = Senec(config['senec_ip'])
if not api:
  sys.exit
data=api.get_values()

#init mail
if config['mail_enabled']:
  smtpObj = smtplib.SMTP(config['mail_server'],config['mail_port']) 
  smtpObj.ehlo()
  smtpObj.starttls()
  smtpObj.login(config['mail_from'], config['mail_password'])

#delete output file
try:
  os.remove(config['outputfile'])
except OSError as e:
  print("Error deleting"+config['outputfile'])
  print(e)
  print("")

def writeValue(x):
  #ausgabe auf console
  if config['consoleout']:
    print(x)

  #ausgabe in datei
  outputfile=config['outputfile']
  if len(outputfile)>0:
    f = open(config['outputfile'], mode='a', encoding='utf-8')
    f.write(x+"\n")
    f.close()

def Modulehandling(ModulIdent,objModuleTemp,objModuleVol):
  writeValue("Modul "+ModulIdent)
  overtemp=False
  # output temp values
  i=int(0) 
  for x in objModuleTemp:
    if int(format(x)) > config['temp_alarm_treshhold']:
      overtemp=True
    writeValue("  Temperatur "+"% s" % i+"               : {0} C".format(x))
    i=i+1 
  # output voltage values
  i=int(0)
  for x in objModuleVol:
    writeValue("  Spannung "+"% 2s" % i+"                : {0} mV".format(x))
    i=i+1
  return overtemp   

def send_mail(body):
  msg = MIMEMultipart()
  msg['Subject'] = config['mail_subject']
  msg['From'] = config['mail_from']
  msg['To'] = config['mail_to']
  msgText = MIMEText('<b>%s</b>' % (body), 'html')
  msg.attach(msgText)
  outputfile=config['outputfile']
  if len(outputfile)>0:
    msg.attach(MIMEText(open(outputfile).read()))
    try:
      with smtplib.SMTP(config['mail_server'], config['mail_port']) as smtpObj:
        smtpObj.ehlo()
        smtpObj.starttls()
        smtpObj.login(config['mail_from'], config['mail_password'])
        smtpObj.sendmail(config['mail_from'], config['mail_to'], msg.as_string())
    except Exception as e:
      print(e)

#reset alarmflag
alarm=False

writeValue("Geraeteinformationen")
writeValue("Aktueller Status    : {0}".format(data["STATISTIC"]['CURRENT_STATE']))
writeValue("Kapazitaet          : {0}".format(data["FACTORY"]['DESIGN_CAPACITY']))
writeValue("Ladeleistung        : {0}".format(data["FACTORY"]['MAX_CHARGE_POWER_DC']))
writeValue("Entladeleistung     : {0}".format(data["FACTORY"]['MAX_DISCHARGE_POWER_DC']))
writeValue("MCU Firmwareversion : {0}".format(data["WIZARD"]['APPLICATION_VERSION']))
writeValue("Steuerungs - SN     : {0}".format(data["FACTORY"]['DEVICE_ID']))

writeValue("")
writeValue("Batterie - Fuellstand        : {0} %".format(round(data["ENERGY"]['GUI_BAT_DATA_FUEL_CHARGE'],2)))
writeValue("Batterie - Laden/Entladen    : {0} W".format(round(data["ENERGY"]['GUI_BAT_DATA_POWER'],2)))
writeValue("Power - Einspeisung / Bezug  : {0} W".format(round(data["ENERGY"]['GUI_GRID_POW'],2)))
writeValue("Power - Hausverbrauch        : {0} W".format(round(data["ENERGY"]['GUI_HOUSE_POW'],2)))
writeValue("Power - PV Leistung          : {0} W".format(round(data["ENERGY"]['GUI_INVERTER_POWER'],2)))
writeValue("")
writeValue("PV Leistung - String 1       : {0} W".format(round(data["PV1"]['MPP_POWER'][0],2)))
writeValue("PV Leistung - String 2       : {0} W".format(round(data["PV1"]['MPP_POWER'][1],2)))
writeValue("PV Leistung - String 3       : {0} W".format(round(data["PV1"]['MPP_POWER'][2],2)))
writeValue("PV Export Ratio              : {0} %".format(round(data["PV1"]['POWER_RATIO'],2)))

writeValue("")
# max capaticity / 2500W = num modules
numModules=int (data["FACTORY"]['DESIGN_CAPACITY']) / 2500
if numModules>=1:
  result=Modulehandling("A",data["BMS"]['CELL_TEMPERATURES_MODULE_A'],data["BMS"]['CELL_VOLTAGES_MODULE_A'])
  alarm=alarm or result

writeValue("")
if numModules>=2:
  result=Modulehandling("B",data["BMS"]['CELL_TEMPERATURES_MODULE_B'],data["BMS"]['CELL_VOLTAGES_MODULE_B'])
  alarm=alarm or result
  
writeValue("")
if numModules>=3:
  alarm=alarm or Modulehandling("C",data["BMS"]['CELL_TEMPERATURES_MODULE_C'],data["BMS"]['CELL_VOLTAGES_MODULE_C'])

writeValue("")
if numModules>=4:
  alarm=alarm or Modulehandling("D",data["BMS"]['CELL_TEMPERATURES_MODULE_D'],data["BMS"]['CELL_VOLTAGES_MODULE_D'])

if config['mail_enabled']:
  if alarm:
    print("sending mail...") 
    send_mail("Battery: Temperature above threshold\n")
from flask import Flask, request
from flask_cors import CORS, cross_origin
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import urllib.request
import math
import requests
import json
import datetime
import smtplib


def sendmail(to, body):
    SUBJECT = 'RED AID - Your Blood was helpful'
    gmail_sender = 'redaid1234@gmail.com'
    gmail_passwd = 'Blooddonation1'
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.ehlo()
    server.starttls()
    server.login(gmail_sender, gmail_passwd)
    BODY = '\r\n'.join(['To: %s' % to,
                        'From: %s' % gmail_sender,
                        'Subject: %s' % SUBJECT,
                        '', body])
    try:
        server.sendmail(gmail_sender, [to], BODY)
        print('email sent')
    except:
        print('error sending email')
    server.quit()


def sendsms(number, message):
    URL = 'https://www.sms4india.com/api/v1/sendCampaign?'
    req_params = {
        'apikey': '0NMMIKICZ7G4F3IJ4GVAT00UF6KV8DZV',
        'secret': '8W7851BZTSOBZ5XW',
        'usetype': 'stage',
        'phone': number,
        'message': message,
        'senderid': 'REDAID'
    }
    for key, value in req_params.items():
        URL+= str(key)+"="+str(value)+'&'
    URL = URL.replace(" ", "%20")
    _ = urllib.request.urlopen(URL[:len(URL)-1])

def verifyAadhaar(aadhaarNumber):
    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    driver = webdriver.Chrome(chrome_options=options)
    driver.get("https://resident.uidai.gov.in/verify")
    element = driver.find_element_by_id("uidno")
    element.send_keys(aadhaarNumber)
    soup = BeautifulSoup(driver.page_source, 'lxml')
    mydivs = soup.findAll("div", {"class": "errormsgClass"})
    element.send_keys(Keys.RETURN)
    driver.close()
    if(mydivs[0]["style"] == "display: block;"):
        return False
    else:
        return True


def initialDbSetup():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS User
                (User_ID INTEGER AUTO_INCREMENT primary key , Name text, DOB date, Aadhar text, Blood_Group text,Email_ID text,PhNo text,verified int,Address1 text,Address2 text, Password text)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Branch
             (Branch_ID INTEGER primary key, Name text,Email_ID text,PhNo text, Password text, Authkey text, Address1 text,Address2 text, Lon float, Lat float)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Cost
             (Branch_ID INTEGER,Blood_Group text,Cost float,primary key(Branch_ID,Blood_Group))''')
    c.execute('''CREATE TABLE IF NOT EXISTS User_Data
             (User_ID INTEGER primary key, Donations int,Requests int, Points float)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Donations
             (D_ID INTEGER AUTO_INCREMENT primary key,Branch_ID text,User_ID text, Blood_Group text,Date_Time datetime,valid int,Aadhar text,Completed int)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Requests
             (R_ID INTEGER AUTO_INCREMENT primary  key,Branch_ID text,User_ID text, Blood_Group text,Date_Time datetime,valid int,Aadhar text,Completed int)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Inventory
             (I_ID INTEGER AUTO_INCREMENT primary  key,Branch_ID text,User_ID text, Blood_Group text,Date_Time datetime,Expiry date,given int)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Payment
             (P_ID INTEGER AUTO_INCREMENT primary  key,Branch_ID text,User_ID text, Blood_Group text,Date_Time datetime,valid int,Aadhar text,Completed int)''')
    conn.close()


initialDbSetup()
app = Flask(__name__)
CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


def degreeToRadians(degrees):
    return degrees * math.pi / 180


def getdistance(lat1, lat2, lon1, lon2):
    earthKm = 6371
    dlat = degreeToRadians(lat2 - lat1)
    dlon = degreeToRadians(lon2 - lon1)
    lat1 = degreeToRadians(lat1)
    lat2 = degreeToRadians(lat2)
    a = math.sin(dlat / 2) ** 2 + math.sin(dlon / 2) ** 2 * \
        math.cos(lat1) * math.cos(lat2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return c * earthKm


@app.route('/addbloodbank', methods=['GET', 'POST', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def addbloodbank():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    if request.method == 'POST':
        data = request.form
        print(data)
        loginid = data['bb-login-id']
        query = "SELECT AuthKey FROM Branch WHERE Branch_ID = ?"
        c.execute(query, (loginid, ))
        res = c.fetchall()
        if(len(res) > 0):
            if(res[0][0] == data['bb-authkey']):
                query = "UPDATE Branch SET Name = ?, Email_ID = ?, PhNo = ?, Password = ?, Address1 = ?, Address2 = ?, Lon = ?, Lat = ? WHERE Branch_ID = ?"
                c.execute(query, (data['bb-name'], data['bb-email'], data['bb-phone'], data['bb-password'],
                                  data['address-line-1'], data['address-line-2'], data['bb-lon'], data['bb-lat'], data['bb-login-id']))
                # c.commit()
                conn.commit()
                return "true"
    return "false"


@app.route('/verifybank', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def verifyBankLogin():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    loginid = data['bb-login-id']
    password = data['bb-login-password']
    query = "SELECT *FROM Branch WHERE Branch_ID = ? AND Password = ?"
    c.execute(query, (loginid, password))
    res = c.fetchall()
    if(len(res) > 0):
        return "true "+str(res[0][0])
    else:
        return "false"


@app.route('/adduser', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def addUser():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    aadhaarnumber = data['signup-ano']
    if(verifyAadhaar(aadhaarnumber) == False):
        return "false aadhaar"
    query = "SELECT User_ID FROM User WHERE Aadhar = ?"
    c.execute(query, (aadhaarnumber, ))
    res = c.fetchall()
    if(len(res) > 0):
        query = "UPDATE User SET Name = ?, DOB = ?, Email_ID = ?, PhNo = ?, verified = ?, Address1 = ?, Address2 = ?, Password = ?"
        c.execute(query, (data['signup-name'], data['signup-dob'], data['signup-emailid'],
                          data['signup-phone'], 1, data['signup-address-1'], data['signup-address-2'], data['signup-pass']))
        conn.commit()
    else:
        query = "INSERT INTO User(Name, DOB, Aadhar, Blood_Group, Email_ID, PhNo, verified, Address1, Address2, Password) VALUES(?,?,?,?,?,?,?,?,?,?)"
        c.execute(query, (data['signup-name'], data['signup-dob'], data['signup-ano'], data['signup-bgroup'], data['signup-emailid'],
                          data['signup-phone'], 0, data['signup-address-1'], data['signup-address-2'], data['signup-pass']))
        conn.commit()
    return "true"


@app.route('/verifyuser', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def verifyUser():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    emailid = data['login-email']
    password = data['login-password']
    query = "SELECT *FROM User WHERE Email_ID = ? AND Password = ?"
    c.execute(query, (emailid, password))
    res = c.fetchall()
    if(len(res) > 0):
        return "true "+str(res[0][0])
    return "false"


@app.route('/getclosestbanks', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def getBloodBanks():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    lat = data['lat']
    lon = data['lon']
    query = "SELECT *FROM Branch"
    c.execute(query)
    res = c.fetchall()
    final_data = []
    for row in res:
        templon = row[8]
        templat = row[9]

        distance = getdistance(float(lat), float(
            templat), float(lon), float(templon))
        print(distance)
        if(distance < 10):
            final_data.append(list(row)+[round(distance, 4)])
    return json.dumps(final_data)


@app.route('/raisedonreq', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def raiseRequest():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    print(data)
    uid = data['uid']
    bid = data['bid']
    query = "SELECT *FROM User WHERE User_ID = ?"
    c.execute(query, (uid, ))
    res = c.fetchone()
    ano = res[3]
    bgrp = res[4]
    timenow = datetime.datetime.now()
    query = "INSERT INTO Donations(Branch_ID, User_ID, Blood_Group, Date_Time, Aadhar, Completed) VALUES (?, ?, ?, ?, ?, ?)"
    c.execute(query, (bid, uid, bgrp, timenow, ano, 0))
    conn.commit()
    return "true"


@app.route('/viewrequests', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def viewRequests():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    bid = data['bid']
    query = "SELECT * FROM Donations WHERE Branch_ID = ? AND Completed = ?"
    c.execute(query, (bid, 0))
    res = c.fetchall()
    final_data = []
    for row in res:
        uid = row[2]
        que = "SELECT Name FROM User WHERE User_ID = ?"
        c.execute(que, (uid, ))
        name = c.fetchone()[0]
        bgrp = row[3]
        rqdt = row[4]
        ano = row[6]
        final_data.append([row[0], name, bgrp, ano, rqdt])
    return json.dumps(final_data)


@app.route('/viewbloodrequests', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def viewBloodRequests():
    hashtable = {'A+': 'ap', 'A-': 'an', 'B+': 'bp', 'B-': 'bn',
                 'O+': 'op', 'O-': 'on', 'AB+': 'abp', 'AB-': 'abn'}
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    bid = data['bid']
    query = "SELECT * FROM Requests WHERE Branch_ID = ? AND Completed = ?"
    c.execute(query, (bid, 0))
    res = c.fetchall()
    print(res)
    final_data = []
    for row in res:
        uid = row[2]
        que = "SELECT Name,Blood_Group, units FROM User WHERE User_ID = ?"
        c.execute(que, (uid, ))
        name, hisbgrp, units = c.fetchone()
        que = "SELECT Cost FROM Cost WHERE Branch_ID = ? AND Blood_Group = ?"
        bgrp = row[3]
        c.execute(que, (bid, hashtable[bgrp]))
        onecost = int(c.fetchone()[0])
        rqdt = row[4]
        ano = row[6]
        noofunits = int(row[8])
        pname = row[9]
        prealtion = row[10]
        purpose = row[11]
        totalcost = 0
        if(bgrp == hisbgrp):
            if units < noofunits:
                totalcost = (onecost*0.3) * int(units) + \
                    (onecost * max(0, noofunits - int(units)))
            else:
                totalcost = (onecost*0.3) * int(noofunits)
        else:
            totalcost = (onecost) * noofunits
        final_data.append([row[0], name, bgrp, ano, rqdt,
                           noofunits, pname, prealtion, purpose, totalcost])
    return json.dumps(final_data)


@app.route('/approvebloodreq', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def approveBloodReq():
    hashtable = {'A+': 'ap', 'A-': 'an', 'B+': 'bp', 'B-': 'bn',
                 'O+': 'op', 'O-': 'on', 'AB+': 'abp', 'AB-': 'abn'}
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    rid = data['rid']
    print(rid)
    query = "UPDATE Requests SET valid = 1, Completed = 1 WHERE R_ID = ?"
    c.execute(query, (rid, ))
    query = "SELECT *FROM Requests WHERE R_ID = ?"
    c.execute(query, (rid, ))
    res = c.fetchone()
    uid = res[2]
    que = "SELECT Name, Blood_Group, units FROM User WHERE User_ID = ?"
    c.execute(que, (uid, ))
    username, mybgrp, myunits = c.fetchone()
    if mybgrp == hashtable[res[3]]:
        updatedUnits = max(0, myunits - res[8])
        que = "UPDATE User SET units = ? WHERE User_ID = ?"
        c.execute(que, (updatedUnits, uid))
    query = "SELECT I_ID, User_ID, Date_Time FROM Inventory WHERE Blood_Group = ? AND Branch_ID = ? AND given = 0 AND discard = 0 ORDER BY Expiry LIMIT ?"
    c.execute(query, (res[3], res[1], res[8]))
    iids = c.fetchall()
    for row in iids:
        que = "UPDATE Inventory SET given = 1 WHERE I_ID = ?"
        c.execute(que, (row[0], ))
        que = "INSERT INTO RI_Table VALUES(?, ?)"
        c.execute(que, (row[0], rid))

    query = "UPDATE Cost SET units = units - ? WHERE Branch_ID = ? AND Blood_Group = ?"
    c.execute(query, (res[8], res[1], hashtable[res[3]]))
    uids = set([(row[1], row[2]) for row in iids])
    for ids, date in uids:
        que = "SELECT Email_ID, PhNo FROM User WHERE User_ID = ?"
        c.execute(que, (ids, ))
        mailid, phoneno = c.fetchone()
        sendmail(mailid, "The Blood you donated on "+date.split(" ")[0]+" was useful to "+username+"for the following purpose: "+res[11]+" . Your help is immensely appretiated.")
        sendsms(str(phoneno), "The Blood you donated on "+date.split(" ")[0]+" was useful to "+username+" for the following purpose: "+res[11]+" . Your help is immensely appretiated.")
    conn.commit()
    return "true"


@app.route('/cancelbloodreq', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def cancelBloodReq():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    rid = data['rid']
    print(rid)
    query = "UPDATE Requests SET valid = 0, Completed = 1 WHERE R_ID = ?"
    c.execute(query, (rid, ))
    # query = "SELECT *FROM Donations WHERE D_ID = ?"
    # c.execute(query, (did, ))
    # res = c.fetchone()
    # uid = res[2]
    conn.commit()
    return "true"


@app.route('/approvedonreq', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def approveDonReq():
    hashtable = {'A+': 'ap', 'A-': 'an', 'B+': 'bp', 'B-': 'bn',
                 'O+': 'op', 'O-': 'on', 'AB+': 'abp', 'AB-': 'abn'}
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    did = data['did']
    print(did)
    query = "UPDATE Donations SET valid = 1, Completed = 1 WHERE D_ID = ?"
    c.execute(query, (did, ))
    query = "SELECT *FROM Donations WHERE D_ID = ?"
    c.execute(query, (did, ))
    res = c.fetchone()
    uid = res[2]
    bid = res[1]
    bgrp = res[3]
    now = datetime.datetime.now()
    expiry = now + datetime.timedelta(days=42)
    query = "UPDATE User SET units = units + 1 WHERE User_ID = ?"
    c.execute(query, (uid, ))
    query = "INSERT INTO Inventory(Branch_ID, User_ID, Blood_Group, Date_Time, Expiry, given) VALUES(?, ?, ?, ?, ? ,?)"
    c.execute(query, (bid, uid, bgrp, now, expiry, 0))
    query = "UPDATE Cost SET units = units + 1 WHERE Branch_ID = ? AND Blood_Group = ?"
    c.execute(query, (bid, hashtable[bgrp]))
    conn.commit()
    return "true"


@app.route('/canceldonreq', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def cancelDonReq():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    did = data['did']
    print(did)
    query = "UPDATE Donations SET valid = 0, Completed = 1 WHERE D_ID = ?"
    c.execute(query, (did, ))
    # query = "SELECT *FROM Donations WHERE D_ID = ?"
    # c.execute(query, (did, ))
    # res = c.fetchone()
    # uid = res[2]
    conn.commit()
    return "true"


@app.route('/getallbanks', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def getallbanks():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    query = "SELECT Name FROM Branch"
    c.execute(query)
    res = c.fetchall()
    return json.dumps(res)


@app.route('/requestblood', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def requestBlood():
    hashtable = {'A+': 'ap', 'A-': 'an', 'B+': 'bp', 'B-': 'bn',
                 'O+': 'op', 'O-': 'on', 'AB+': 'abp', 'AB-': 'abn'}
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    query = "SELECT Branch_ID FROM Branch WHERE Name = ?"
    c.execute(query, (data['bank'], ))
    bid = c.fetchone()[0]
    bgrp = hashtable[data['bgrp']]
    query = "SELECT units FROM Cost WHERE Branch_ID = ? AND Blood_Group = ?"
    c.execute(query, (bid, bgrp))
    res = c.fetchone()[0]
    if(int(res) < int(data['noofunits'])):
        return "false "+str(res)
    query = "SELECT Aadhar FROM User WHERE User_ID = ?"
    c.execute(query, (data['uid'], ))
    ano = c.fetchone()[0]
    reqdt = datetime.datetime.now()
    query = "INSERT INTO Requests(Branch_ID, User_ID, Blood_group, Date_Time, Aadhar, Completed, noofunits, PatientName, Relation, Purpose) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    c.execute(query, (bid, data['uid'], data['bgrp'], reqdt, ano, 0, data['noofunits'],
                      data['patientname'], data['patientrelation'], data['purpose']))
    conn.commit()
    return "true"


@app.route('/getbloodcost', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def getBloodCost():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    bid = data['bid']
    query = "SELECT * FROM Cost WHERE Branch_ID = ?"
    c.execute(query, (bid, ))
    res = c.fetchall()
    return json.dumps(res)


@app.route('/updatecosts', methods=['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def updateCosts():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    print(data)
    bid = data['bid']
    data = dict(data)
    del data['bid']
    for key, value in data.items():
        query = "UPDATE Cost SET Cost = ? WHERE Branch_ID = ? AND Blood_Group = ?"
        c.execute(query, (value, bid, key))
    conn.commit()
    return "true"

@app.route('/userhistory', methods = ['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def userHistory():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    uid = data['uid']
    query = "SELECT *FROM Donations WHERE User_ID = ?"
    c.execute(query, (uid, ))
    res = c.fetchall()
    query = "SELECT *FROM Requests WHERE User_ID = ?"
    c.execute(query, (uid, ))
    res2 = c.fetchall()
    final_res = res + res2
    final_res = sorted(final_res, key=lambda x: x[4], reverse=True)
    print(final_res)
    print(res2)
    return json.dumps(final_res)


@app.route('/personalinfo', methods = ['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def personalInfo():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    uid = data['uid']
    query = "SELECT *FROM User WHERE User_ID = ?"
    c.execute(query, (uid, ))
    res = c.fetchone()
    return json.dumps(res)

@app.route('/getmaxdate', methods = ['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def getMaxDate():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    uid = data['uid']
    query = "SELECT MAX(Date_Time) FROM Donations WHERE User_ID = ?"
    c.execute(query, (uid, ))
    res = c.fetchone()[0]
    if res == None:
        return str(datetime.datetime.now())
    date = datetime.datetime.strptime(res, r"%Y-%m-%d %H:%M:%S.%f")
    date = date + datetime.timedelta(days=90)
    return str(date)

@app.route('/discardbags', methods = ['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def discardBags():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    query = "SELECT I_ID, Expiry FROM Inventory"
    c.execute(query)
    res = c.fetchall()
    for iid, date in res:
        olddate = datetime.datetime.strptime(date, r"%Y-%m-%d %H:%M:%S.%f")
        if olddate < datetime.datetime.now():
            que = "UPDATE Inventory SET discard = ? WHERE I_ID = ?"
            c.execute(que, (1, iid))
        conn.commit()
    return "true"

@app.route('/getdiscardedbags', methods = ['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def getdiscarded():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    bid = data['bid']
    query = "SELECT *FROM Inventory WHERE Branch_ID = ? AND discard = ?"
    c.execute(query, (bid, 1))
    res = c.fetchall()
    return json.dumps(res)

@app.route('/getinventory', methods = ['POST', 'GET', 'OPTIONS'])
@cross_origin(supports_credentials=True, origin="*")
def getInventory():
    conn = sqlite3.connect('BloodDonation.db')
    c = conn.cursor()
    data = request.form
    bid = data['bid']
    query = "SELECT *FROM Cost WHERE Branch_ID = ?"
    c.execute(query, (bid, ))
    res = c.fetchall()
    return json.dumps(res)
if __name__ == "__main__":
    app.run(debug=True)

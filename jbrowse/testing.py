#!/usr/bin/python

import unittest
import requests
import db

#note these tests could ping the server so the server must be running in another terminal before testing
# test these by running the following command
# python testing.py

#TODO write a test to simulate running R code here
#Yuanyuan?

class UnitTestCases(unittest.TestCase):
    def testSanityCheck(self):
        self.failUnless(True)
    def testDBGetPut(self):
        testDB = db.testDB
        testDB.put("test", "1234")
        self.failUnlessEqual("1234", testDB.get("test"))
    def testDBMoreValues(self):
        testDB = db.testDB
        testDB.put("testing", "1234")
        testDB.put("test", "4321")
        self.failIfEqual("4321", testDB.get("testing"))
    def testServerSendsOK(self):
        resp = requests.post("http://localhost:8081", data={u'start': 95745719, u'end': 95748599, u'ref': u'chr1', u'name': u'interactive'}, headers={'Content-Type':'application/json'})
        self.failUnlessEqual(True, resp.ok)


if __name__ =='__main__':
    unittest.main()

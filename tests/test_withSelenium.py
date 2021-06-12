import os
import sys
import time
import pytest
import signal
import shutil
import tarfile
import unittest
import selenium
import threading
import subprocess
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

url = 'http://localhost.com:8080'
dataDir = os.path.join('jbrowse', 'jbrowse', 'data')
dbDir = os.path.join(dataDir, 'db')
dbTar = os.path.join('data', 'db.tar.gz')


class PeakLearnerTests(unittest.TestCase):
    dataDir = os.path.join('jbrowse', 'jbrowse', 'data')
    dbDir = os.path.join(dataDir, 'db')
    dbTar = os.path.join('data', 'db.tar.gz')

    def setUp(self):
        if os.path.exists(self.dbDir):
            shutil.rmtree(self.dbDir)

        if not os.path.exists(self.dbDir):
            with tarfile.open(self.dbTar) as tar:
                tar.extractall(self.dataDir)

        self.host = subprocess.Popen(['uwsgi', 'wsgi.ini'],
                                     stdout=subprocess.PIPE)

        try:
            self.driver = webdriver.Chrome()
        except WebDriverException:
            self.driver = webdriver.Chrome('chromedriver')
        self.driver.set_window_size(1280, 667)

    def tearDown(self):
        os.kill(self.host.pid, signal.SIGTERM)
        self.driver.close()

    def test_LOPART_model(self):
        self.driver.get(url)

        self.driver.find_element(By.ID, 'myHubs').click()

        self.driver.find_element(By.ID, 'publicHubLink').click()

        self.moveToDefinedLocation()

        self.selectTracks(numTracks=6)

        for i in range(4):
            self.zoomIn()

        tracks = self.driver.find_elements(By.CLASS_NAME, 'track_peaklearnerbackend_view_track_model')

        assert len(tracks) == 6

        # Check that there is a model missing somewhere which can be filled in via LOPART
        modelMissing = False

        for track in tracks:
            models = []
            for block in track.find_elements(By.CLASS_NAME, 'block'):
                blockModels = block.find_elements(By.CLASS_NAME, 'Model')

                if len(blockModels) == 0:
                    continue

                for modelDiv in blockModels:
                    models.append({'size': modelDiv.size, 'location': modelDiv.location})


            if len(models) < 1:
                modelMissing = True

        assert modelMissing

        self.enableLopart()

        self.addPeak(2257, width=120)

        time.sleep(2)

        tracks = self.driver.find_elements(By.CLASS_NAME, 'track_peaklearnerbackend_view_track_model')

        assert len(tracks) == 6

        for track in tracks:
            labels = []
            models = []
            labelNoText = []
            for block in track.find_elements(By.CLASS_NAME, 'block'):
                # Blocks contain canvas and divs for labels/models
                for div in block.find_elements(By.CLASS_NAME, 'Label'):
                    try:
                        labelText = div.find_element(By.CLASS_NAME, 'LabelText')
                    except selenium.common.exceptions.NoSuchElementException:
                        labelBody = div.find_element(By.CLASS_NAME, 'LabelBody')

                        labelNoText.append({'size': labelBody.size,
                                            'location': labelBody.location,
                                            'start': labelBody.location['x'],
                                            'end': labelBody.location['x'] + labelBody.size['width']})
                        continue

                    if labelText.text in ['peakStart', 'peakEnd']:
                        labelBody = div.find_element(By.CLASS_NAME, 'LabelBody')

                        labels.append({'label': labelText.text,
                                       'size': labelBody.size,
                                       'location': labelBody.location,
                                       'start': labelBody.location['x'],
                                       'end': labelBody.location['x'] + labelBody.size['width']})

                blockModels = block.find_elements(By.CLASS_NAME, 'Model')

                if len(blockModels) == 0:
                    continue

                for modelDiv in blockModels:
                    models.append({'size': modelDiv.size, 'location': modelDiv.location})

            shouldBeModel = False

            # check if the noText labels can be appended to a label from a different block
            for labelNo in labelNoText:
                for label in labels:
                    if labelNo['start'] == label['end']:

                        label['end'] = labelNo['end']
                        label['size']['width'] = label['size']['width'] + labelNo['size']['width']

                        if label['label'] in ['peakStart', 'peakEnd']:
                            shouldBeModel = True

            # If there should be a model, check that there is a model being displayed
            if shouldBeModel:
                assert len(models) > 0

            for model in models:
                start = model['location']['x']
                end = start + model['size']['width']

                inStart = inEnd = False

                for label in labels:
                    if label['label'] == 'peakStart':
                        if label['start'] < start < label['end']:
                            inStart = True
                    elif label['label'] == 'peakEnd':
                        if label['start'] < end < label['end']:
                            inEnd = True

                assert inStart

                assert inEnd

    def addPeak(self, midPoint, width=40):
        labelWidth = width / 2

        self.addLabel('peakStart', midPoint - labelWidth, midPoint - 1)

        time.sleep(0.5)

        self.addLabel('peakEnd', midPoint, midPoint + labelWidth)

        time.sleep(0.5)

    def addLabel(self, labelType, start, end):
        wait = WebDriverWait(self.driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, "track_aorta_ENCFF115HTK")))

        labelDropdown = self.driver.find_element(By.ID, 'current-label')

        labelDropdown.click()

        labelMenu = self.driver.find_element(By.ID, 'current-label_dropdown')

        options = labelMenu.find_elements(By.XPATH, './/*')

        for option in options:
            if option.tag_name == 'tr':
                label = option.get_attribute('aria-label')

                if label is None:
                    continue

                # Space at end or something
                if label.strip() == labelType:
                    option.click()
                    break

        element = self.driver.find_element(By.ID, 'highlight-btn')

        element.click()

        track = self.driver.find_element(By.ID, 'track_aorta_ENCFF115HTK')

        action = ActionChains(self.driver)

        action.move_to_element_with_offset(track, start, 50)

        action.click_and_hold().perform()

        action.move_by_offset(end - start, 50)

        action.release().perform()

        wait.until(EC.presence_of_element_located((By.ID, "track_aorta_ENCFF115HTK")))

    def zoomIn(self):
        wait = WebDriverWait(self.driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, "bigZoomIn")))

        element = self.driver.find_element(By.ID, 'bigZoomIn')

        element.click()

        time.sleep(2)

    def zoomOut(self):
        wait = WebDriverWait(self.driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, "bigZoomOut")))

        element = self.driver.find_element(By.ID, 'bigZoomOut')

        element.click()

        time.sleep(2)

    def selectTracks(self, numTracks=0):
        wait = WebDriverWait(self.driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, "hierarchicalTrackPane")))

        element = self.driver.find_element(By.ID, "hierarchicalTrackPane")

        checkboxes = element.find_elements(By.TAG_NAME, 'input')

        if numTracks == 0:
            numTracks = len(checkboxes)

        tracks = []

        # Load all available tracks
        for checkbox in checkboxes:
            parent = checkbox.find_element(By.XPATH, '..')
            trackName = parent.text

            # Not sure why I need to check for this but okay
            if trackName == '' or 'Input' in trackName:
                continue
            checkbox.click()
            tracks.append(trackName)
            trackId = 'track_%s' % trackName
            wait.until(EC.presence_of_element_located((By.ID, trackId)))
            numTracks -= 1
            if numTracks < 1:
                break

    def enableLopart(self):
        wait = WebDriverWait(self.driver, 15)

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "peaklearner")))

        self.driver.find_element(By.CLASS_NAME, 'peaklearner').click()

        popup = self.driver.find_element(By.ID, 'dijit_PopupMenuItem_0_text')

        action = ActionChains(self.driver)

        action.move_to_element(popup).perform()

        time.sleep(1)

        self.driver.find_element(By.ID, 'LOPART').click()

    def moveToDefinedLocation(self):
        # Move to defined location

        wait = WebDriverWait(self.driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, 'search-box')))

        searchbox = self.driver.find_element(By.ID, 'search-box')

        chromDropdown = searchbox.find_element(By.ID, 'search-refseq')

        chromDropdown.click()

        menu = self.driver.find_element(By.ID, 'dijit_form_Select_0_menu')

        options = menu.find_elements(By.XPATH, './/*')

        # Go to chr3 chrom
        for option in options:
            if option.tag_name == 'tr':
                label = option.get_attribute('aria-label')

                if label is None:
                    continue

                # Space at end or something
                if label.strip() == 'chr3':
                    option.click()
                    break

        assert 'chr3' in self.driver.title

        # Move location now
        elem = searchbox.find_element(By.ID, 'widget_location')
        nav = elem.find_element(By.ID, 'location')
        nav.clear()

        # not sure why navigating here goes to the url below but it does it seemingly every time so
        nav.send_keys('93504855..194041961')

        go = searchbox.find_element(By.ID, 'search-go-btn_label')

        go.click()

        assert "93462708..193999814" in self.driver.title

    def scrollUp(self):
        wait = WebDriverWait(self.driver, 15)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'vertical_position_marker')))

        # scroll to top of page
        element = self.driver.find_element(By.CLASS_NAME, 'vertical_position_marker')

        action = ActionChains(self.driver)

        action.move_to_element(element)

        # Not sure why I need an extra 100 pixels but it works
        y = element.location.get('y') + 100

        action.drag_and_drop_by_offset(element, 0, -y)

        action.perform()

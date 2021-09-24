import os
import sys
import time
import random
import selenium
from tests import Base
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from multiprocessing import Process
import asyncio
import uvicorn
import faulthandler

faulthandler.enable(sys.stderr, all_threads=True)
waitTime = 60

host = 'localhost'
port = 8080
url = 'http://%s:%s' % (host, port)

if not os.path.exists('screenshots'):
    os.makedirs('screenshots')


class CheckExistsInTrack(object):
    """Checks that the particular class exists in that element

  locator - used to find the element
  returns the WebElement once it has the particular css class
  """

    def __init__(self, elementToCheck, classToCheck):
        self.element = elementToCheck
        self.classToCheck = classToCheck

    def __call__(self, driver):
        element = driver.find_element(By.ID, self.element.get_attribute('id'))  # Finding the referenced element
        classToCheck = element.find_elements(By.CLASS_NAME, self.classToCheck)

        if len(classToCheck):
            return True
        else:
            return False


class TitleChanges(object):
    """Checks that the particular class exists in that element

  locator - used to find the element
  returns the WebElement once it has the particular css class
  """

    def __init__(self, title):
        self.title = title

    def __call__(self, driver):
        title = driver.title  # Finding the referenced element

        if title != self.title:
            return True
        else:
            return False


class PeakLearnerTests(Base.PeakLearnerAsyncTestBase):
    user = 'Public'
    hub = 'H3K4me3_TDH_ENCODE'

    async def setUp(self):
        await super().setUp()

        import core.main as main

        self.proc = Process(target=uvicorn.run,
                            args=(main.app,),
                            kwargs={
                                "host": host,
                                "port": port,
                                "log_level": "info"},
                            daemon=True)
        self.proc.start()
        await asyncio.sleep(1)

        options = Options()
        try:
            if os.environ['TESTING'].lower() == 'true':
                options.headless = True
        except KeyError:
            pass
        try:
            self.driver = webdriver.Chrome(options=options)
        except WebDriverException:
            try:
                self.driver = webdriver.Chrome('chromedriver', options=options)
            except WebDriverException:
                self.driver = webdriver.Chrome('/buildtools/webdriver/chromedriver', options=options)
        self.driver.set_window_size(1280, 667)

    # This test is mainly here so that when this file is ran on CI, it will have a genomes file for hub.
    def test_AddHub(self):
        self.driver.get(url)

        self.driver.find_element(By.ID, 'myHubs').click()

        self.driver.find_element(By.ID, 'uploadHubButton').click()

        hubUrl = 'https://rcdata.nau.edu/genomic-ml/PeakLearner/testHub/hub.txt'
        self.driver.find_element(By.ID, 'hubUrl').send_keys(hubUrl)

        self.driver.find_element(By.ID, 'submitButton').click()

        wait = WebDriverWait(self.driver, 5)
        wait.until(EC.presence_of_element_located((By.ID, 'search-box')))

    def test_LOPART_model(self):
        self.runAltModelTest('lopart')

    def test_FLOPART_model(self):
        self.runAltModelTest('flopart')

    def runAltModelTest(self, whichModel):
        self.driver.get(url)

        self.driver.find_element(By.ID, 'myHubs').click()

        self.driver.find_element(By.ID, '(\'Public\', \'H3K4me3_TDH_ENCODE\')_publicHubLink').click()

        self.moveToDefinedLocation()

        self.selectTracks(numTracks=3)

        for i in range(4):
            self.zoomIn()

        tracks = self.driver.find_elements(By.CLASS_NAME, 'track_peaklearnerbackend_view_track_model')

        assert len(tracks) == 3

        self.enableAltModel(whichModel)

        self.addPeak(2295, width=120, genModel=True)

        tracks = self.driver.find_elements(By.CLASS_NAME, 'track_peaklearnerbackend_view_track_model')

        assert len(tracks) == 3

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

                for label in labels:
                    if label['label'] == 'peakStart':
                        if label['start'] < start < label['end']:
                            label['inStart'] = True
                    elif label['label'] == 'peakEnd':
                        if label['start'] < end < label['end']:
                            label['inEnd'] = True

            for label in labels:
                fail = 0
                try:
                    assert label['inEnd']
                except KeyError:
                    fail += 1

                try:
                    assert label['inStart']
                except KeyError:
                    fail += 1

                if fail == 2:
                    raise Exception

    def test_JobsPage_Working(self):
        self.driver.get(url)

        self.driver.find_element(By.ID, 'statsNav').click()

        self.driver.find_element(By.ID, 'jobStats').click()

        self.checkIfError()

    def test_moreInfoPage_Working(self):
        self.driver.get(url)

        self.driver.find_element(By.ID, 'myHubs').click()

        hubId = '%s-%s-hubInfo-showMore' % (self.user, self.hub)

        self.driver.find_element(By.ID, hubId).click()

        self.checkIfError()

    def test_goToLabeledRegion(self):
        self.goToRegion('labeled')

    def test_goToUnlabeledRegion(self):
        self.goToRegion('unlabeled')

    def test_resize(self):
        self.driver.get(url)

        self.driver.find_element(By.ID, 'myHubs').click()

        self.driver.find_element(By.ID, '(\'Public\', \'H3K4me3_TDH_ENCODE\')_publicHubLink').click()

        self.moveToDefinedLocation()

        # Zoom in once so just incase it goes to the defined location region which is labeled already
        self.zoomIn()

        title = self.driver.title

        self.selectTracks(numTracks=3)

        track = self.driver.find_element(By.ID, 'track_aorta_ENCFF115HTK')

        oldHeight = track.size['height']

        wait = WebDriverWait(self.driver, waitTime)

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "view")))

        self.driver.find_element(By.CLASS_NAME, 'view').click()

        wait.until(EC.presence_of_element_located((By.ID, "dropdownmenu_view")))

        wait.until(EC.presence_of_element_located((By.ID, "menubar_settrackheight_text")))
        self.driver.find_element(By.ID, 'menubar_settrackheight_text').click()

        wait.until(EC.presence_of_element_located((By.ID, 'dijit_form_NumberSpinner_0')))

        text = self.driver.find_element(By.ID, 'dijit_form_NumberSpinner_0')

        text.clear()

        text.send_keys('50')

        ok = self.driver.find_element(By.ID, 'dijit_form_Button_1_label')

        ok.click()

        track = self.driver.find_element(By.ID, 'track_aorta_ENCFF115HTK')

        assert oldHeight != track.size['height']



    def goToRegion(self, region):
        self.driver.get(url)

        self.driver.find_element(By.ID, 'myHubs').click()

        self.driver.find_element(By.ID, '(\'Public\', \'H3K4me3_TDH_ENCODE\')_publicHubLink').click()

        self.moveToDefinedLocation()

        # Zoom in once so just incase it goes to the defined location region which is labeled already
        self.zoomIn()

        title = self.driver.title

        self.selectTracks(numTracks=3)

        wait = WebDriverWait(self.driver, waitTime)

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "peaklearner")))

        self.driver.find_element(By.CLASS_NAME, 'peaklearner').click()

        if region == 'labeled':
            elementId = 'labeledRegion'
        else:
            elementId = 'unlabeledRegion'

        self.driver.find_element(By.ID, elementId).click()

        wait = WebDriverWait(self.driver, waitTime)

        wait.until(TitleChanges(title))

    def checkIfError(self):
        # Assert that the page is working to begin with
        try:
            element = self.driver.find_element(By.ID, 'main-frame-error')

            # If here, then prev line didn't error
            assert 1 == 0
        except selenium.common.exceptions.NoSuchElementException:
            if '404' in self.driver.title:
                raise Exception('404 Exception')

    def addPeak(self, midPoint, width=40, genModel=False):
        labelWidth = width / 2

        self.addLabel('peakStart', midPoint - labelWidth, midPoint - 1, genModel=genModel)

        self.addLabel('peakEnd', midPoint, midPoint + labelWidth, genModel=genModel)

    def addLabel(self, labelType, start, end, genModel=False):
        wait = WebDriverWait(self.driver, waitTime)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "track_peaklearnerbackend_view_track_model")))

        tracks = self.driver.find_elements(By.CLASS_NAME, 'track_peaklearnerbackend_view_track_model')

        trackLabels = {}

        for track in tracks:
            trackLabels[track.get_attribute('id')] = len(track.find_elements(By.CLASS_NAME, 'Label'))

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

        action.pause(1)

        action.move_to_element_with_offset(track, start, 50)

        action.pause(1)

        action.click_and_hold()

        action.pause(1)

        action.move_by_offset(end - start, 50)

        action.pause(1)

        action.release().pause(1).perform()

        wait.until(EC.presence_of_element_located((By.ID, "track_aorta_ENCFF115HTK")))

        tracks = self.driver.find_elements(By.CLASS_NAME, 'track_peaklearnerbackend_view_track_model')

        try:
            for track in tracks:
                trackWait = WebDriverWait(self.driver, waitTime)
                trackWait.until(CheckExistsInTrack(track, 'Label'))
                if genModel:
                    trackWait.until(CheckExistsInTrack(track, 'Model'))
        except selenium.common.exceptions.TimeoutException:
            self.driver.save_screenshot('screenshots/%s.png' % random.random())
            raise

    def zoomIn(self):
        wait = WebDriverWait(self.driver, waitTime)
        wait.until(EC.presence_of_element_located((By.ID, "bigZoomIn")))

        element = self.driver.find_element(By.ID, 'bigZoomIn')

        element.click()

        time.sleep(2)

    def zoomOut(self):
        wait = WebDriverWait(self.driver, waitTime)
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
            if checkbox.get_attribute('class') == 'hierachcheck':
                continue
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

    def enableAltModel(self, whichModel):
        wait = WebDriverWait(self.driver, waitTime)

        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "peaklearner")))

        self.driver.find_element(By.CLASS_NAME, 'peaklearner').click()

        wait.until(EC.visibility_of_element_located((By.ID, 'dijit_PopupMenuItem_0_text')))

        popup = self.driver.find_element(By.ID, 'dijit_PopupMenuItem_0_text')

        action = ActionChains(self.driver)

        action.move_to_element(popup)
        action.pause(1).perform()

        wait.until(EC.visibility_of_element_located((By.ID, 'modelTypeMenu')))

        self.driver.find_element(By.ID, whichModel.upper()).click()

        time.sleep(5)

    def moveToDefinedLocation(self):
        # Move to defined location

        wait = WebDriverWait(self.driver, waitTime)
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

        assert "chr3:934" in self.driver.title

    def scrollUp(self):
        wait = WebDriverWait(self.driver, waitTime)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'vertical_position_marker')))

        # scroll to top of page
        element = self.driver.find_element(By.CLASS_NAME, 'vertical_position_marker')

        action = ActionChains(self.driver)

        action.move_to_element(element)

        # Not sure why I need an extra 100 pixels but it works
        y = element.location.get('y') + 100

        action.drag_and_drop_by_offset(element, 0, -y)

        action.perform()

    async def tearDown(self):
        """ Shutdown the app. """

        self.proc.terminate()

        for entry in self.driver.get_log('browser'):
            print(entry)

        self.driver.close()

        super().tearDown()

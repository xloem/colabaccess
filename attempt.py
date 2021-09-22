import os

from selenium import webdriver
from webdriver_setup import get_webdriver_for
from pyshadow.main import Shadow

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class GoogleDriver:
    SIGNINGIN_ELEMENT_ID = 'captchaimg'
    SIGNEDIN_ELEMENT_ID = 'wiz_jd'
    def __init__(self, engine = 'firefox', dir = os.path.join('~','.config','google-webdriver')):
        dir = os.path.expanduser(dir)
        self.engine = engine
        self.dir = os.path.join(dir, self.engine)
        self.create()
    def create(self):
        os.makedirs(self.dir, exist_ok=True)
        if self.engine == 'firefox':
            options = webdriver.FirefoxOptions()
            options.profile = self.dir
            options.headless = True
            #ff_options.add_argument('--headless')
            self.webdriver = get_webdriver_for('firefox', options=options)
            self.webdriver.get('https://accounts.google.com/')
            WebDriverWait(self.webdriver, 10).until(EC.presence_of_element_located((By.ID, 'base-js')))
            if self.webdriver.find_elements_by_id(GoogleDriver.SIGNINGIN_ELEMENT_ID):
                # not logged in
                raise Exception('Not logged in.  Please run this, login, exit, and try again: XRE_PROFILE_PATH="' + self.dir + '" firefox')
            elif not self.webdriver.find_elements_by_id(GoogleDriver.SIGNEDIN_ELEMENT_ID):
                raise Exception("element ids unrecognised, please update SIGNINGIN_ELEMENT_ID and SIGNEDIN_ELEMENT_ID in source code to reflect element ids that indicate needing to sign or, or being signed in, at https://accounts.google.com/ .  Ids in a page can be found in the developer console in a web browser using hardcoded element ids in source code using: console.log(JSON.stringify(Array.prototype.map.call(document.querySelectorAll('*[id]'), x=>x.id)))")
        #elif engine == 'chrome':
        #    options = webdriver.ChromeOptions()
        #    options.
        else:
            raise Exception('unimplemented engine:', engine)
        #self.xvfb = Xvfb()
        #chrome_options = webdriver.ChromeOptions()
        #chrome_options.add_argument('--user-data-dir=' + user_data_dir)
        #self.xvfb.start()
        #self.webdriver = webdriver.Chrome(options=chrome_options)
        #self.webdriver.get('https://accounts.google.com/')
        #if 'Sign' in self.webdriver.title:
        #    # WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'password')))
        #    self.xvfb.stop()
        #    self.webdriver = webdriver.Chrome(options=chrome_options)
        #    self.webdriver.get('https://accounts.google.com/')
        return self.webdriver
        
driver = GoogleDriver()

class Colab:
    # these are collected here to make them easy to update
    def BASEURL():
        return 'https://colab.research.google.com/'

    def NEW_NOTEBOOK(webdriver):
        webdriver.get(Colab.BASEURL() + '#create=true')

    def CONDITIONS_NOTEBOOK_LOADED():
        return EC.presence_of_element_located((By.ID, 'doc-name'))

    def GET_NOTEBOOK_NAME(webdriver):
        return webdriver.find_element_by_id('doc-name').get_attribute('value')

    def SET_NOTEBOOK_NAME(webdriver, newname):
        name = webdriver.find_element_by_id('doc-name')
        name.clear()
        name.send_keys(newname, Keys.RETURN)
        return name.get_attribute('value')

    def CELL_ELEMENTS(webdriver):
        return webdriver.find_elements_by_class_name('cell')

    def INSERT_CELL_BELOW_CURRENT(webdriver):
        webdriver.find_element_by_id('toolbar-add-code').click()

    def RUN_CELL(webdriver, shadow, cell_element):
        cell_element.click()
        outer = cell_element.find_element_by_tag_name('colab-run-button')
        inner = shadow.find_element(outer, '.cell-execution')
        inner.click()

    def IS_RUN_COMPLETE(webdriver, shadow, cell_element):
        outer = cell_element.find_element_by_tag_name('colab-run-button')
        # div id status
        return bool(shadow.find_elements(outer, '#status'))

    def GET_CELL_TEXT(cell_element):
        try:
            return cell_element.find_element_by_tag_name('textarea').get_attribute('value')
        except:
            return cell_element.find_element_by_class_name('main-content').text

    def GET_CELL_OUTPUT_CONTAINER(webdriver, cell_element):
        output = cell_element.find_element_by_class_name('output')
        iframes = output.find_elements_by_tag_name('iframe')
        if iframes:
            webdriver.switch_to.frame(iframes[0])
            result = webdriver.find_element_by_id('output-body')
            webdriver.switch_to.default_content()
        else:
            renderers = output.find_elements_by_tag_name('colab-static-output-renderer')
            if renderers:
                result = renderers[0]
            else:
                result = output
        return result

    def GET_CELL_OUTPUT(webdriver, cell_element):
        return Colab.GET_CELL_OUTPUT_CONTAINER(webdriver, cell_element).text

    def GENERATE_CELL_OUTPUT(webdriver, shadow, cell_element):
        last_output = None
        next_output = None
        def output_changed():
            nonlocal last_output, next_output
            next_output = Colab.GET_CELL_OUTPUT(webdriver, cell_element)   
            return next_output != last_output
        output_changed()
        yield next_output
        last_output = next_output
        while not Colab.IS_RUN_COMPLETE(webdriver, shadow, cell_element):
            commonprefix = os.path.commonprefix((next_output, last_output))
            yield next_output[len(commonprefix):]
            last_output = next_output
            WebDriverWait(webdriver, 60*60).until(output_changed)

    def SET_CELL_TEXT(webdriver, cell_element, text):
        editor = cell_element.find_element_by_class_name('monaco-editor')
        editor.click()
        lines = cell_element.find_element_by_tag_name('textarea')
        # erase existing content
        ActionChains(webdriver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
        lines.send_keys(Keys.DELETE)
        editor.click()
        # type new content.  character by character to handle indentation adjustment.
        sent = ''
        for char in text:
            _nextchar = False
            while True:
                state = Colab.GET_CELL_TEXT(cell_element)
                #print('state=', state, 'sent=', sent)
                if state == sent:
                    break
                commonprefix = os.path.commonprefix((state, text))
                if len(commonprefix) > len(sent):
                    sent += commonprefix[len(sent)]
                    _nextchar = True
                    break
                else:
                    lines.send_keys(Keys.END, Keys.BACKSPACE)
                    continue
            if _nextchar:
                continue
            #print('sending', char)
            lines.send_keys(char)
            sent += char
        return sent

    def RESTART_RUNTIME(webdriver):
        webdriver.find_element_by_id('runtime-menu-button').click()
        webdriver.find_element_by_id('runtime-menu').find_element_by_xpath('//div[@command="restart"]').click()
        
    def OPEN_DIALOG(webdriver):
        webdriver.find_element_by_id('file-menu-button').click()
        webdriver.find_element_by_id('file-menu').find_element_by_xpath('//div[@command="open"]').click()
    def OPEN_DISMISS(webdriver):
        webdriver.find_element_by_class_name('dismiss').click()

    def A_DIALOG_IS_PRESENT(webdriver):
        return bool(webdriver.find_elements_by_tag_name('paper-dialog'))
    def CLOSE_DIALOG(webdriver, shadow):
        # first wait for buttons to be enabled

        # the aria-disabled attribute of the paper-button elements is 'false' when can be clicked, 'true' when unclickable
        dialog = webdriver.find_element_by_tag_name('paper-dialog')
        WebDriverWait(webdriver, 10).until(lambda webdriver: shadow.find_element(dialog, 'paper-button').get_attribute('aria-disabled') != 'true')

        # click button
        try:
            shadow.find_element(dialog, '#ok').click()
        except:
            shadow.find_element(dialog, '.dismiss').click()

        # wait for dialog to go away
        WebDriverWait(webdriver, 10).until(lambda webdriver: not Colab.A_DIALOG_IS_PRESENT(webdriver))

    class Cell:
        def __init__(self, colab, element):
            self.colab = colab
            self.element = element
        def run(self):
            Colab.RUN_CELL(self.colab.webdriver, self.colab.shadow, self.element)
            if Colab.A_DIALOG_IS_PRESENT(self.colab.webdriver):
                Colab.CLOSE_DIALOG(self.colab.webdriver, self.colab.shadow)
            return self.stream
        @property
        def text(self):
            return Colab.GET_CELL_TEXT(self.element)
        @text.setter
        def text(self, text):
            return Colab.SET_CELL_TEXT(self.colab.webdriver, self.element, text)
        @property
        def output(self):
            return Colab.GET_CELL_OUTPUT(self.colab.webdriver, self.element)
        @property
        def stream(self):
            return Colab.GENERATE_CELL_OUTPUT(self.colab.webdriver, self.colab.shadow, self.element)

        @property
        def is_run_complete(self):
            return Colab.IS_RUN_COMPLETE(self.colab.webdriver, self.colab.shadow, self.element)

        def __str__(self):
            return self.text + '\n' + self.output

        def __repr__(self):
            return str(self)
            
    def __init__(self, googledriver, url = None):
        if url is None:
            url = Colab.BASEURL()
        self.googledriver = googledriver
        self.webdriver = googledriver.webdriver
        self.shadow = Shadow(self.webdriver)
        self.open(url)
    def reconnect(self):
        self.googledriver.create()
        self.webdriver = self.googledriver.webdriver
    def open(self, url):
        self.webdriver.get(url)
        self._wait_for_loaded()
    def new(self):
        Colab.NEW_NOTEBOOK(self.webdriver)
        self._wait_for_loaded()
        return self.name
    def restart(self):
        Colab.RESTART_RUNTIME(self.webdriver)
    def insert_cell_below(self):
        Colab.INSERT_CELL_BELOW_CURRENT(self.webdriver)
    @property
    def cells(self):
        return [
            Colab.Cell(self, cell)
            for cell in Colab.CELL_ELEMENTS(self.webdriver)
        ]
    @property
    def name(self):
        return Colab.GET_NOTEBOOK_NAME(self.webdriver)
    @name.setter
    def doc_name(self, name):
        Colab.SET_NOTEBOOK_NAME(self.webdriver, name)
    def _wait_for_loaded(self):
        WebDriverWait(self.webdriver, 10).until(Colab.CONDITIONS_NOTEBOOK_LOADED())

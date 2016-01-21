'use strict';

// #############################################################################
// Change Settings behaviour

var globals = require('./settings/globals');
var casperjs = require('casper');
var cms = require('./helpers/cms')(casperjs);
var xPath = casperjs.selectXPath;

casper.test.setUp(function (done) {
    casper.start()
        .then(cms.login())
        .then(cms.addPage({ title: 'home' }))
        .then(cms.addPlugin({
            type: 'TextPlugin',
            content: {
                id_body: 'Dummy to create history'
            }
        }))
        .then(cms.addPlugin({
            type: 'TextPlugin',
            content: {
                id_body: 'Test-text'
            }
        }))
        .run(done);
});

casper.test.tearDown(function (done) {
    casper.start()
        .then(cms.removePage())
        .then(cms.logout())
        .run(done);
});

casper.test.begin('History', function (test) {
    casper
        .start(globals.editUrl)
        .then(function () {
        .waitUntilVisible('.cms-toolbar-expanded', function () {
            test.assertElementCount(
                '.cms-dragarea:nth-child(1) > .cms-draggables > .cms-draggable',
                2,
                'Both plugins are in first placeholder'
            );
        })
        // click on History
        .waitUntilVisible('.cms-toolbar-expanded', function () {
            // click on History
            this.click(
                // mouse clicks on the History link
                xPath('//a[.//span[text()[contains(.,"History")]]]')
            );
        })
        // click on Undo
        .waitForSelector('.cms-toolbar-item-navigation-hover', function () {
        .wait(10, function () {
            this.click(
                // mouse clicks on the Undo link
                xPath('//a[.//span[text()[contains(.,"Undo")]]]')
            );
        })
        .waitForResource(/undo/)
        .waitWhileVisible('.cms-toolbar-expanded')
        .waitUntilVisible('.cms-toolbar-expanded', function () {
            // Clicking again on undo after resource have been loaded
            this.click(
                // mouse clicks on the History link
                xPath('//a[.//span[text()[contains(.,"History")]]]')
            );
        })
        .waitForSelector('.cms-toolbar-item-navigation-hover', function () {
        .wait(10, function () {
            this.click(
                // mouse clicks on the Undo link
                xPath('//a[.//span[text()[contains(.,"Undo")]]]')
            );
        })
        .waitForResource(/undo/)
        .waitWhileVisible('.cms-toolbar-expanded')
        .waitUntilVisible('.cms-toolbar-expanded', function () {
            // Counts plugins in the first placeholder if there's only one
            test.assertElementCount(
                '.cms-dragarea:nth-child(1) > .cms-draggables > .cms-draggable',
                1,
                'Second plugin is removed'
            );
        })
        // click on History
        .waitUntilVisible('.cms-toolbar-expanded', function () {
            this.click(
                // mouse clicks on the History link
                xPath('//a[.//span[text()[contains(.,"History")]]]')
            );
        })
        // click on Redo
        .waitForSelector('.cms-toolbar-item-navigation-hover', function () {
        .wait(10, function () {
            this.click(
                // mouse clicks on the Redo link
                xPath('//a[.//span[text()[contains(.,"Redo")]]]')
            );
        })
        // Clicking again on redo after resource have been loaded
        .waitForResource(/redo/)
        .waitWhileVisible('.cms-toolbar-expanded')
        .waitUntilVisible('.cms-toolbar-expanded', function () {
            this.click(
                // mouse clicks on the History link
                xPath('//a[.//span[text()[contains(.,"History")]]]')
            );
        })
        .waitForSelector('.cms-toolbar-item-navigation-hover', function () {
        .wait(10, function () {
            this.click(
                // mouse clicks on the redo link
                xPath('//a[.//span[text()[contains(.,"Redo")]]]')
            );
        })
        // Counts if there are two plugin in the first placeholder
        .waitForResource(/redo/)
        .waitWhileVisible('.cms-toolbar-expanded')
        .waitUntilVisible('.cms-toolbar-expanded', function () {
            test.assertElementCount(
                '.cms-dragarea:nth-child(1) > .cms-draggables > .cms-draggable',
                2,
                'Both Plugin are back'
            );
            this.click('.cms-toolbar-item-navigation > li:nth-child(3) > a');
        })
        // Clicks on View history
        .waitForSelector('.cms-toolbar-item-navigation-hover', function () {
        .wait(10, function () {
            this.click(
                // mouse clicks on the redo link
                xPath('//a[.//span[text()[contains(.,"View history...")]]]')
            );
        })
        // Wait for modal
        .withFrame(0, function () {
            casper.waitForSelector('#change-history', function () {
                test.assertExists('#change-history', 'The page creation wizard form is available');
                // clicks on the second row of the history table (which had one plugin)
                this.click('tr:nth-child(2) th a ');
            })
            // waits that the form gets loaded
            .waitForSelector('#page_form', function () {
                test.assertExists('#page_form', 'Page Form loaded');
            });
        })
        // clicks on the save button
        .then(function () {
            this.click('.cms-modal-item-buttons .cms-btn-action');
        })
        // counts again that there is only one plugin
        .waitForResource(/cms\/page\/\d+\/history/)
        .waitUntilVisible('.cms-toolbar-expanded', function () {
            test.assertElementCount(
                '.cms-dragarea:nth-child(1) > .cms-draggables > .cms-draggable',
                1,
                'History reverted'
            );
        })
        .run(function () {
            test.done();
        });
});

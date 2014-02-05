(function (requirejs, require, define) {

// VideoSpeedControl module.
define(
'video/08_video_speed_control.js',
[],
function () {

    // VideoSpeedControl() function - what this module "exports".
    return function (state) {
        var dfd = $.Deferred();

        if (state.isTouch) {
            // iOS doesn't support speed change
            state.el.find('div.speeds').remove();
            dfd.resolve();
            return dfd.promise();
        }

        state.videoSpeedControl = {};

        _initialize(state);
        dfd.resolve();

        if (state.videoType === 'html5' && !(_checkPlaybackRates())) {
            console.log(
                '[Video info]: HTML5 mode - playbackRate is not supported.'
            );

            _hideSpeedControl(state);
        }

        return dfd.promise();
    };

    // ***************************************************************
    // Private functions start here.
    // ***************************************************************

    function _initialize(state) {
        _makeFunctionsPublic(state);
        _renderElements(state);
        _bindHandlers(state);
    }

    // function _makeFunctionsPublic(state)
    //
    //     Functions which will be accessible via 'state' object. When called,
    //     these functions will get the 'state' object as a context.
    function _makeFunctionsPublic(state) {
        var methodsDict = {
            changeVideoSpeed: changeVideoSpeed,
            reRender: reRender,
            setSpeed: setSpeed
        };

        state.bindTo(methodsDict, state.videoSpeedControl, state);
    }

    // function _renderElements(state)
    //
    //     Create any necessary DOM elements, attach them, and set their
    //     initial configuration. Also make the created DOM elements available
    //     via the 'state' object. Much easier to work this way - you don't
    //     have to do repeated jQuery element selects.
    function _renderElements(state) {
        state.videoSpeedControl.speeds = state.speeds;

        state.videoSpeedControl.el = state.el.find('div.speeds');

        state.videoSpeedControl.videoSpeedsEl = state.videoSpeedControl.el
            .find('.video_speeds');

        state.videoControl.secondaryControlsEl.prepend(
            state.videoSpeedControl.el
        );

        $.each(state.videoSpeedControl.speeds, function (index, speed) {
            var link = '<a class="speed_link" href="#">' + speed + 'x</a>';

            state.videoSpeedControl.videoSpeedsEl
                .prepend(
                    $('<li data-speed="' + speed + '">' + link + '</li>')
                );
        });

        state.videoSpeedControl.setSpeed(state.speed);
    }

    /**
     * @desc Check if playbackRate supports by browser.
     *
     * @type {function}
     * @access private
     *
     * @param {object} state The object containg the state of the video player.
     *     All other modules, their parameters, public variables, etc. are
     *     available via this object.
     *
     * @this {object} The global window object.
     *
     * @returns {Boolean}
     *       true: Browser support playbackRate functionality.
     *       false: Browser doesn't support playbackRate functionality.
     */
    function _checkPlaybackRates() {
        var video = document.createElement('video');

        // If browser supports, 1.0 should be returned by playbackRate
        // property. In this case, function return True. Otherwise, False will
        // be returned.
        return Boolean(video.playbackRate);
    }

    // Hide speed control.
    function _hideSpeedControl(state) {
        state.el.find('div.speeds').hide();
    }

    // Get previous element in array or cyles back to the last if it is the
    // first.
    function _previousSpeedLink(speedLinks, index) {
        return speedLinks.eq(index < 1 ? speedLinks.length - 1 : index - 1);
    }

    // Get next element in array or cyles back to the first if it is the last.
    function _nextSpeedLink(speedLinks, index) {
        return speedLinks.eq(index >= speedLinks.length - 1 ? 0 : index + 1);
    }

    /**
     * @desc Bind any necessary function callbacks to DOM events (click,
     *     mousemove, etc.).
     *
     * @type {function}
     * @access private
     *
     * @param {object} state The object containg the state of the video player.
     *     All other modules, their parameters, public variables, etc. are
     *     available via this object.
     *
     * @this {object} The global window object.
     *
     * @returns {undefined}
     */
    function _bindHandlers(state) {
        var speedLinks,
            KEY = $.ui.keyCode;

        state.videoSpeedControl.videoSpeedsEl.find('a')
            .on('click', state.videoSpeedControl.changeVideoSpeed);

        if (state.isTouch) {
            state.videoSpeedControl.el.on('click', function (event) {
                // So that you can't highlight this control via a drag
                // operation, we disable the default browser actions on a
                // click event.
                event.preventDefault();

                state.videoSpeedControl.el.toggleClass('open');
            });
        } else {
            state.videoSpeedControl.el
                .on('mouseenter', function () {
                    state.videoSpeedControl.el.addClass('open');
                })
                .on('mouseleave', function () {
                    state.videoSpeedControl.el.removeClass('open');
                })
                .on('click', function (event) {
                    // So that you can't highlight this control via a drag
                    // operation, we disable the default browser actions on a
                    // click event.
                    event.preventDefault();

                    state.videoSpeedControl.el.removeClass('open');
                })
                // Attach 'keydown' event to speed control.
                .on('keydown', function(event) {
                    var keyCode = event.keyCode;
                    if (keyCode !== KEY.TAB) {
                        event.preventDefault();
                        event.stopImmediatePropagation();
                    }
                    // Open menu and focus on last element of list above it.
                    if (keyCode === KEY.ENTER || keyCode === KEY.SPACE ||
                        keyCode === KEY.UP) {
                        state.videoSpeedControl.el.addClass('open');
                        state.videoSpeedControl.videoSpeedsEl
                                               .find('a.speed_link:last')
                                               .focus();
                    }
                    // Close menu.
                    else if (keyCode === KEY.ESCAPE) {
                        state.videoSpeedControl.el.removeClass('open');
                    }
                });

            // Attach 'keydown' event to the individual speed entries.
            speedLinks = state.videoSpeedControl.videoSpeedsEl
                .find('a.speed_link');

            speedLinks.each(function(index, speedLink) {
                var previousSpeedLink = _previousSpeedLink(speedLinks, index),
                    nextSpeedLink = _nextSpeedLink(speedLinks, index),
                    speedButtonAnchor = state.videoSpeedControl.el
                                                               .children('a');

                $(speedLink).on('keydown', function (event) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                    switch (event.keyCode) {
                        // Scroll up menu, wrapping at the top. Keep menu open.
                        case KEY.UP:
                            $(previousSpeedLink).focus();
                            break;
                        // Scroll down  menu, wrapping at the bottom. Keep menu
                        // open.
                        case KEY.DOWN:
                            $(nextSpeedLink).focus();
                            break;
                        // Close menu.
                        case KEY.TAB:
                            state.videoSpeedControl.el.removeClass('open');
                            // Set focus to previous menu button in menu bar
                            // (Play/Pause button)
                            if (event.shiftKey) {
                                state.videoControl.playPauseEl .focus();
                            }
                            // Set focus to next menu button in menu bar
                            // (Volume button)
                            else {
                                state.videoVolumeControl.buttonEl.focus();
                            }
                            break;
                        // Close menu, give focus to speed control and change
                        // speed.
                        case KEY.ENTER:
                            state.videoSpeedControl.el.removeClass('open');
                            speedButtonAnchor.focus();
                            state.videoSpeedControl.changeVideoSpeed(event);
                            break;
                        // Close menu and give focus to speed control.
                        case KEY.ESCAPE:
                            state.videoSpeedControl.el.removeClass('open');
                            speedButtonAnchor.focus();
                            break;
                    }
                });
            });
        }
    }

    // ***************************************************************
    // Public functions start here.
    // These are available via the 'state' object. Their context ('this'
    // keyword) is the 'state' object. The magic private function that makes
    // them available and sets up their context is makeFunctionsPublic().
    // ***************************************************************

    function setSpeed(speed) {
        this.videoSpeedControl.videoSpeedsEl.find('li').removeClass('active');
        this.videoSpeedControl.videoSpeedsEl
            .find("li[data-speed='" + speed + "']")
            .addClass('active');
        this.videoSpeedControl.el.find('p.active').html('' + speed + 'x');
    }

    function changeVideoSpeed(event) {
        var parentEl = $(event.target).parent();

        event.preventDefault();

        if (!parentEl.hasClass('active')) {
            this.videoSpeedControl.currentSpeed = parentEl.data('speed');

            this.videoSpeedControl.setSpeed(
                // To meet the API expected format.
                parseFloat(this.videoSpeedControl.currentSpeed)
                    .toFixed(2)
                    .replace(/\.00$/, '.0')
            );

            this.trigger(
                'videoPlayer.onSpeedChange',
                this.videoSpeedControl.currentSpeed
            );
        }
        // When a speed entry has been selected, we want the speed control to
        // regain focus.
        parentEl.parent().siblings('a').focus();
    }

    function reRender(params) {
        var _this = this;

        this.videoSpeedControl.videoSpeedsEl.empty();
        this.videoSpeedControl.videoSpeedsEl.find('li').removeClass('active');
        this.videoSpeedControl.speeds = params.newSpeeds;

        $.each(this.videoSpeedControl.speeds, function (index, speed) {
            var link, listItem;

            link = '<a class="speed_link" href="#" role="menuitem">' + speed + 'x</a>';

            listItem = $('<li data-speed="' + speed + '" role="presentation">' + link + '</li>');

            if (speed === params.currentSpeed) {
                listItem.addClass('active');
            }

            _this.videoSpeedControl.videoSpeedsEl.prepend(listItem);
        });

        // Re-attach all events with their appropriate callbacks to the
        // newly generated elements.
        _bindHandlers(this);
    }

});

}(RequireJS.requirejs, RequireJS.require, RequireJS.define));

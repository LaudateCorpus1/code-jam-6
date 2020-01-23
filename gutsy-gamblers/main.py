from datetime import datetime, timedelta, date
import pickle

import kivy
import requests
from kivy.animation import Animation
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import Metrics
from kivy.properties import NumericProperty
from kivy.uix.effectwidget import EffectWidget, HorizontalBlurEffect, VerticalBlurEffect, EffectBase
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager

from suntime import Sun, SunTimeException


kivy.require('1.11.1')


hv_blur = """
vec4 effect(vec4 color, sampler2D texture, vec2 tex_coords, vec2 coords)
{{
    float dt = ({} / 4.0) * 1.0 / resolution.x;
    vec4 sum = vec4(0.0);
    sum += texture2D(texture, vec2(tex_coords.x - 4.0*dt, tex_coords.y))
                     * 0.05;
    sum += texture2D(texture, vec2(tex_coords.x - 3.0*dt, tex_coords.y))
                     * 0.09;
    sum += texture2D(texture, vec2(tex_coords.x - 2.0*dt, tex_coords.y))
                     * 0.12;
    sum += texture2D(texture, vec2(tex_coords.x - dt, tex_coords.y))
                     * 0.15;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y))
                     * 0.16;
    sum += texture2D(texture, vec2(tex_coords.x + dt, tex_coords.y))
                     * 0.15;
    sum += texture2D(texture, vec2(tex_coords.x + 2.0*dt, tex_coords.y))
                     * 0.12;
    sum += texture2D(texture, vec2(tex_coords.x + 3.0*dt, tex_coords.y))
                     * 0.09;
    sum += texture2D(texture, vec2(tex_coords.x + 4.0*dt, tex_coords.y))
                     * 0.05;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y - 4.0*dt))
                     * 0.05;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y - 3.0*dt))
                     * 0.09;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y - 2.0*dt))
                     * 0.12;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y - dt))
                     * 0.15;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y))
                     * 0.16;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y + dt))
                     * 0.15;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y + 2.0*dt))
                     * 0.12;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y + 3.0*dt))
                     * 0.09;
    sum += texture2D(texture, vec2(tex_coords.x, tex_coords.y + 4.0*dt))
                     * 0.05;
    return vec4(sum.xyz, color.w);
}}
"""


class TimeController:
    clock_multiplier = 5000
    date_iterate = 0

    def __init__(self):
        pass

    def sun_angles(self, date_iterate):
        with open('latlong.tmp', 'rb') as f:
            lat_long = pickle.load(f)

        print(date_iterate)

        sun_time = Sun(lat_long[0], lat_long[1])
        current_date = datetime.now() + timedelta(days=date_iterate)

        try:
            today_sunrise = sun_time.get_sunrise_time(current_date)
        except SunTimeException:
            raise ValueError("AINT NO SUNSHINE WHEN SHE'S GONE")

        try:
            today_sunset = sun_time.get_sunset_time(current_date)
        except SunTimeException:
            raise ValueError("HOLY SHIT TOO MUCH SUNSHINE WHEN SHE'S HERE")

        # This is *super* ugly, I'm sure we can find a more elegant way to do this
        now = datetime.utcnow() - timedelta(hours=0)
        today_sunrise = today_sunrise.replace(tzinfo=None)
        today_sunset = today_sunset.replace(tzinfo=None)

        # After Sunrise, after Sunset
        if now > today_sunrise and today_sunset:
            # Get timedelta for each
            today_sunrise = now - today_sunrise
            today_sunset = now - today_sunset

            # Convert timedelta into minutes and round
            today_sunrise = round(today_sunrise.seconds / 60)
            today_sunset = round(today_sunset.seconds / 60)

            # Convert minutes into angles
            today_sunrise = today_sunrise * 0.25
            today_sunset = today_sunset * 0.25

        # Before Sunrise, after Sunset
        elif now < today_sunrise and today_sunset:
            today_sunrise = today_sunrise - now
            today_sunset = today_sunset - now

            today_sunrise = round(today_sunrise.seconds / 60)
            today_sunset = round(today_sunset.seconds / 60)

            today_sunrise = 360 - (today_sunrise * 0.25)
            today_sunset = 360 - (today_sunset * 0.25)

        # After Sunrise, before Sunset
        else:
            today_sunrise = now - today_sunrise
            today_sunset = today_sunset - now

            today_sunrise = round(today_sunrise.seconds / 60)
            today_sunset = round(today_sunset.seconds / 60)

            today_sunrise = today_sunrise * 0.25
            today_sunset = 360 - (today_sunset * 0.25)

        return today_sunrise, today_sunset


# Widget element things #
class DialWidget(FloatLayout):
    """
    Speed will become a fixed value of 86400 once completed.
    Image should, i suppose, be a fixed image?
    At some point we'll need to add a tuple(?) for sunrise / sunset times.
    """
    angle = NumericProperty(0)

    def __init__(self, day_length, dial_size, **kwargs):
        super(DialWidget, self).__init__(**kwargs)

        self.date_iterate = 0
        self.dial_size = dial_size

        # Split suntime tuple into named variables
        self.sun_angles = TimeController().sun_angles(self.date_iterate)
        self.sunrise = self.sun_angles[0]
        self.sunset = self.sun_angles[1]

        self.test_date = 0

        # Duration is how long it takes to perform the overall animation
        anim = Animation(angle=360, duration=day_length)
        anim += Animation(angle=360, duration=day_length)
        anim.repeat = True
        anim.start(self)

        # Shading widget
        self.dial_shading = DialEffectWidget((self.sunrise, self.sunset))

        # Add icons that can be arbitrarily rotated on canvas.
        self.sun_rise_marker = SunRiseMarker(self.sunrise)
        self.sun_set_marker = SunSetMarker(self.sunset)

        # Add widgets
        self.add_widget(self.dial_shading)
        self.add_widget(self.sun_rise_marker)
        self.add_widget(self.sun_set_marker)

        self.clock = Clock.schedule_interval(self.redraw, 2.5)

    def redraw(self, a):
        self.date_iterate += 10

        self.remove_widget(self.dial_shading)
        self.remove_widget(self.sun_rise_marker)
        self.remove_widget(self.sun_set_marker)

        sun_angles = TimeController().sun_angles(self.date_iterate)

        # Split suntime tuple into named variables
        self.sunrise = sun_angles[0]
        self.sunset = sun_angles[1]

        # Shading widget
        self.dial_shading = DialEffectWidget((self.sunrise, self.sunset))

        # Add icons that can be arbitrarily rotated on canvas.
        self.sun_rise_marker = SunRiseMarker(self.sunrise)
        self.sun_set_marker = SunSetMarker(self.sunset)

        # Add widgets
        self.add_widget(self.dial_shading)
        self.add_widget(self.sun_rise_marker)
        self.add_widget(self.sun_set_marker)

        self.clock = Clock.schedule_interval(self.redraw, 2.5)

    def on_angle(self, item, angle):
        if angle == 360:
            item.angle = 0


class DoubleVision(EffectBase):
    size = NumericProperty(4.0)

    def __init__(self, *args, **kwargs):
        super(DoubleVision, self).__init__(*args, **kwargs)
        self.do_glsl()

    def on_size(self, *args):
        self.do_glsl()

    def do_glsl(self):
        self.glsl = hv_blur.format(float(self.size))


class DialEffectWidget(EffectWidget):
    def __init__(self, angles, **kwargs):
        super(DialEffectWidget, self).__init__(**kwargs)

        self.shade_size = Window.height * 0.8, Window.height * 0.8
        self.add_widget(SunShading(angles))
        # self.effects = [HorizontalBlurEffect(size=50.0), VerticalBlurEffect(size=50.0)]
        self.effects = [DoubleVision(size=50.0)]
        self.opacity = 0.25

    def _pos_check(self):
        if Window.width > Window.height:
            self.shade_size = Window.height * 0.8, Window.height * 0.8
        else:
            self.shade_size = Window.width * 0.8, Window.width * 0.8


class SunShading(FloatLayout):
    def __init__(self, angles, **kwargs):
        super(SunShading, self).__init__(**kwargs)

        rise_angle = angles[0]
        set_angle = angles[1]

        sun_colour = (0.9, 0.9, 0.08, 1)
        shade_colour = (0.0, 0.2, 0.4, 1)

        # More of bisks brutally ugly work
        if rise_angle < set_angle:
            self.shade_one_angle_start = 360 - set_angle
            self.shade_one_angle_stop = 360 - rise_angle
            self.shade_one_color = shade_colour

            self.sun_one_angle_start = 0
            self.sun_one_angle_stop = 360 - set_angle
            self.sun_one_color = sun_colour
            self.sun_two_angle_start = 360 - rise_angle
            self.sun_two_angle_stop = 360
            self.sun_two_color = sun_colour

        elif rise_angle > set_angle:
            self.shade_one_angle_start = 360 - set_angle
            self.shade_one_angle_stop = 360
            self.shade_one_color = shade_colour
            self.shade_two_angle_start = 360 - rise_angle
            self.shade_two_angle_stop = 0
            self.shade_two_color = shade_colour

            self.sun_one_angle_start = 360 - rise_angle
            self.sun_one_angle_stop = 360 - set_angle
            self.sun_one_color = sun_colour

        self.shade_size = Window.height * 0.8, Window.height * 0.8

    def _size_check(self):
        self.shade_size = Window.height * 0.8, Window.height * 0.8


class SunRiseMarker(FloatLayout):
    def __init__(self, rot_angle, **kwargs):
        super(SunRiseMarker, self).__init__(**kwargs)
        self.rot_angle = rot_angle


class SunSetMarker(FloatLayout):
    def __init__(self, rot_angle, **kwargs):
        super(SunSetMarker, self).__init__(**kwargs)
        self.rot_angle = rot_angle


class NowMarker(FloatLayout):
    pass


# Screens in the App #
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)

        self.add_widget(DialWidget(86400, (0.8, 0.8)))
        self.add_widget(NowMarker())

    def on_size(self, a, b):
        # Maintains a constant aspect ratio of 0.5625 (16:9)
        width, height = Window.size

        if not Window.fullscreen and (height / width) != 0.5625:
            height = width * 0.5625

        width /= Metrics.density
        height /= Metrics.density

        Window.size = (width, height)

    def time_control_button(self):
        time_control_popup = TimeWizard()
        time_control_popup.open()

    def settings_button(self):
        SettingsScreen()

    def ipgeolocate(self):
        resp = requests.get('http://ip-api.com/json/').json()

        # pickle the object for testing purposes
        temp_latlong = [resp['lat'], resp['lon']]
        with open('latlong.tmp', 'wb') as f:
            pickle.dump(temp_latlong, f)

        return resp['lat'], resp['lon']


# Time control panel
class TimeWizard(Popup):
    def __init__(self, **kwargs):
        super(TimeWizard, self).__init__(**kwargs)


# Settings panel #
class SettingsScreen(Popup):
    def __init__(self, **kwargs):
        super(SettingsScreen, self).__init__(**kwargs)

        resp = requests.get('http://ip-api.com/json/').json()
        city = resp['city']
        region = resp['regionName']
        country = resp['country']

        settings_popup = Popup(title="Settings",
                               content=Label(
                                   text=f'Currently in {city}, {region}, {country}'
                               ),
                               size_hint=(None, None), size=(500, 200))
        settings_popup.open()


class WindowManager(ScreenManager):
    pass


class SunClock(App):
    """
    Core class.
    """
    def build(self):
        Builder.load_file('main.kv')
        sm = WindowManager()

        screens = [MainScreen(name='main')]
        for screen in screens:
            sm.add_widget(screen)

        # Don't forget to change this shit back.
        sm.current = 'main'

        return sm


if __name__ == '__main__':
    SunClock().run()

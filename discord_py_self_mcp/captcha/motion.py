import random
import time
import math
import numpy as np
from typing import List, Tuple

def bezier_curve(p0, p1, p2, p3, n_points=100):
    """
    Generate points for a cubic bezier curve.
    """
    t = np.linspace(0, 1, n_points)
    points = []
    for i in t:
        x = (1-i)**3*p0[0] + 3*(1-i)**2*i*p1[0] + 3*(1-i)*i**2*p2[0] + i**3*p3[0]
        y = (1-i)**3*p0[1] + 3*(1-i)**2*i*p1[1] + 3*(1-i)*i**2*p2[1] + i**3*p3[1]
        points.append((x, y))
    return points

class LocalMotionGenerator:
    """
    Generates human-like mouse movements locally using Bezier curves.
    Replaces the need for external API.
    """
    def __init__(self):
        pass

    def generate_movement(self, start: Tuple[int, int], end: Tuple[int, int], duration: float = None) -> List[List[int]]:
        """
        Generate a list of [x, y, time] points from start to end.
        """
        x1, y1 = start
        x2, y2 = end
        
        dist = math.hypot(x2 - x1, y2 - y1)
        if duration is None:
            # Estimate duration based on distance (speed ~ 1000px/s to 2000px/s)
            speed = random.uniform(0.8, 1.5)  # pixels per ms? No, that's too fast. 
            # Human speed: ~500-1000 pixels per second.
            # dist (px) / speed (px/ms) = time (ms)
            # 1000 px/s = 1 px/ms.
            duration = (dist / random.uniform(0.8, 1.5)) + random.uniform(100, 200)

        # Control points for Bezier curve (randomize to look human)
        # p1 and p2 should be somewhere between start and end, with some randomness
        
        # Vector from start to end
        dx = x2 - x1
        dy = y2 - y1
        
        # Perpendicular vector
        px = -dy
        py = dx
        
        # Normalize
        norm = math.hypot(px, py)
        if norm == 0:
            px, py = 0, 0
        else:
            px /= norm
            py /= norm
            
        # Random offset
        offset1 = random.uniform(-dist/4, dist/4)
        offset2 = random.uniform(-dist/4, dist/4)
        
        p1 = (x1 + dx*0.3 + px*offset1, y1 + dy*0.3 + py*offset1)
        p2 = (x1 + dx*0.7 + px*offset2, y1 + dy*0.7 + py*offset2)
        
        # Generate points
        points = bezier_curve(start, p1, p2, end, n_points=int(duration/10)) # One point every ~10ms
        
        # Add timestamps
        result = []
        current_time = 0
        dt = duration / len(points)
        
        for px, py in points:
            # Add some jitter
            jitter_x = random.uniform(-1, 1)
            jitter_y = random.uniform(-1, 1)
            
            result.append([
                int(px + jitter_x), 
                int(py + jitter_y), 
                int(current_time)
            ])
            current_time += dt
            
        return result

# Re-implement data structures from original motion.py
class rectangle:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def get_dimensions(self) -> Tuple:
        return self.width, self.height

    def get_box(self, rel_x: int, rel_y: int) -> Tuple:
        rel_x = int(rel_x)
        rel_y = int(rel_y)
        return (rel_x, rel_y), (rel_x + self.width, rel_y + self.height)

    def get_corners(self, rel_x: int = 0, rel_y: int = 0) -> List:
        rel_x = int(rel_x)
        rel_y = int(rel_y)
        return [(rel_x, rel_y), (rel_x + self.width, rel_y), (rel_x, rel_y + self.height), (rel_x + self.width, rel_y + self.height)]

class widget_check:
    def __init__(self, rel_position: Tuple) -> None:
        self.widget = rectangle(300, 75)
        self.check_box = rectangle(28, 28)
        self.rel_position = rel_position

    def get_check(self) -> Tuple:
        return self.check_box.get_box(16 + self.rel_position[0], 23 + self.rel_position[1])

    def get_closest(self, position: Tuple) -> Tuple:
        corners = self.widget.get_corners(self.rel_position[0], self.rel_position[1])
        sorted_corners = sorted(corners, key=lambda c: math.hypot(c[0] - position[0], c[1] - position[1]))
        return sorted_corners[0], sorted_corners[1]

COMMON_SCREEN_SIZES = [
    (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
    (1280, 720), (1600, 900), (2560, 1440), (1680, 1050)
]
COMMON_CORE_COUNTS = [4, 8, 6, 12, 2, 16]
COMMON_COLOR_DEPTHS = [24, 30]
COMMON_LANGUAGES = [
    ('en-US', ['en-US', 'en']), ('en-GB', ['en-GB', 'en']), ('en', ['en']),
    ('es-ES', ['es-ES', 'es']), ('fr-FR', ['fr-FR', 'fr']), ('de-DE', ['de-DE', 'de']),
    ('ja-JP', ['ja-JP', 'ja']), ('zh-CN', ['zh-CN', 'zh']),
]

class get_cap:
    def __init__(self, user_agent: str, href: str, screen_size: Tuple = None) -> None:
        self.user_agent = user_agent
        if screen_size is None:
            screen_size = random.choice(COMMON_SCREEN_SIZES)
        self.screen_size = screen_size
        self.color_depth = random.choice(COMMON_COLOR_DEPTHS)
        self.hardware_concurrency = random.choice(COMMON_CORE_COUNTS)
        self.language, self.languages = random.choice(COMMON_LANGUAGES)
        
        widget_id = '0' + ''.join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=10))
        
        # Calculate random point safely within bounds
        max_x = max(1, screen_size[0] - 150)
        max_y = max(1, screen_size[1] - 38)
        self.rel_position = (random.randint(0, max_x), random.randint(0, max_y))
        
        self.widget = widget_check(self.rel_position)
        self.position = (random.randint(0, screen_size[0]), random.randint(0, screen_size[1]))
        
        self.motion_gen = LocalMotionGenerator()
        
        self.data = {
            'st': int(time.time() * 1000),
            'mm': [], 'mm-mp': 0,
            'md': [], 'md-mp': 0,
            'mu': [], 'mu-mp': 0,
            'v': 1,
            'topLevel': self.top_level(),
            'session': [],
            'widgetList': [widget_id],
            'widgetId': widget_id,
            'href': href,
            'prev': {'escaped': False, 'passed': False, 'expiredChallenge': False, 'expiredResponse': False}
        }

        # Generate movement to checkbox
        check_box_rect = self.widget.get_check()
        goal_x = random.randint(check_box_rect[0][0], check_box_rect[1][0])
        goal_y = random.randint(check_box_rect[0][1], check_box_rect[1][1])
        goal = (goal_x, goal_y)
        
        self.mouse_movement = self.motion_gen.generate_movement(self.position, goal)
        
        start_point = self.rel_position
        self.data['mm'] = [[x - start_point[0], y - start_point[1], t] for x, y, t in self.mouse_movement]
        
        # Calculate mean period
        timestamps = [x[-1] for x in self.mouse_movement]
        if len(timestamps) > 1:
            periods = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            self.data['mm-mp'] = sum(periods) / len(periods)
        
        # Mouse down/up events
        last_mm = self.data['mm'][-1]
        timestamp = int(time.time() * 1000)
        self.data['md'].append([last_mm[0], last_mm[1], timestamp])
        time.sleep(random.uniform(0.05, 0.15))
        self.data['mu'].append([last_mm[0], last_mm[1], timestamp + random.randint(50, 150)])

    def top_level(self) -> dict:
        taskbar_height = random.choice([0, 30, 40, 48])
        avail_height = max(1, self.screen_size[1] - taskbar_height)
        
        data = {
            'inv': False,
            'st': int(time.time() * 1000),
            'sc': {
                'availWidth': self.screen_size[0], 'availHeight': avail_height,
                'width': self.screen_size[0], 'height': self.screen_size[1],
                'colorDepth': self.color_depth, 'pixelDepth': self.color_depth,
                'top': 0, 'left': 0, 'availTop': 0, 'availLeft': 0,
                'mozOrientation': 'landscape-primary', 'onmozorientationchange': None
            },
            'nv': {
                'permissions': {}, 'pdfViewerEnabled': True,
                'doNotTrack': random.choice(['unspecified', None, '1', '0']),
                'maxTouchPoints': 0, 'mediaCapabilities': {},
                'vendor': 'Google Inc.', 'vendorSub': '', 'cookieEnabled': True,
                'mediaDevices': {}, 'serviceWorker': {}, 'credentials': {},
                'clipboard': {}, 'mediaSession': {}, 'webdriver': False,
                'hardwareConcurrency': self.hardware_concurrency,
                'geolocation': {}, 'userAgent': self.user_agent,
                'language': self.language, 'languages': self.languages,
                'locks': {}, 'onLine': True, 'storage': {},
                'plugins': ['internal-pdf-viewer'] if random.random() > 0.3 else []
            },
            'dr': '', 'exec': False,
            'wn': [[self.screen_size[0], self.screen_size[1], 1, int(time.time() * 1000)]],
            'wn-mp': 0, 'xy': [[0, 0, 1, int(time.time() * 1000)]],
            'xy-mp': 0, 'mm': [], 'mm-mp': 0
        }

        # Initial movement (simulated)
        position = self.position
        closest = self.widget.get_closest(position)
        
        # Pick random point on closest edge
        goal_x = random.randint(min(closest[0][0], closest[1][0]), max(closest[0][0], closest[1][0]))
        goal_y = random.randint(min(closest[0][1], closest[1][1]), max(closest[0][1], closest[1][1]))
        goal = (goal_x, goal_y)
        
        mouse_movement = self.motion_gen.generate_movement(position, goal)
        self.position = goal
        
        data['mm'] = mouse_movement
        timestamps = [x[-1] for x in mouse_movement]
        if len(timestamps) > 1:
            periods = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
            data['mm-mp'] = sum(periods) / len(periods)

        return data

class motion_data:
    def __init__(self, user_agent: str, url: str, screen_size: Tuple = None) -> None:
        self.user_agent = user_agent
        self.url = url
        self.get_captcha_motion_data = get_cap(self.user_agent, self.url, screen_size)

    def get_captcha(self) -> dict:
        return self.get_captcha_motion_data.data

    def check_captcha(self) -> dict:
        return self.get_captcha_motion_data.data

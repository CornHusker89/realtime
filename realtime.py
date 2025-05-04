# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Realtime",
    "author": "CornHusker",
    "description": "Simple timer for each workspace in a blender project", 
    "blender": (4, 2, 0),
    "version": (1, 0, 1),
    "location": "View3D > Sidebar > Realtime",
    "warning" : "",
    "doc_url": "", 
    "tracker_url": "", 
    "category" : "User Interface" 
}

import bpy
import datetime
import json
from typing import Dict


class Session():

    @staticmethod
    def from_json(json_str) -> "Session":
        data = json.loads(json_str)
        start_time = datetime.datetime.strptime(data["st"], "%Y-%m-%d %H:%M:%S")
        end_time = datetime.datetime.strptime(data["et"], "%Y-%m-%d %H:%M:%S") if data["et"] else None
        duration = data["d"]
        render_time = data["rt"]
        full_time = data["ft"]
        active_time = data["at"]
        inactive_time = data["iat"]
        workspace_time = json.loads(data["wt"])
        return Session(start_time, end_time, render_time, full_time, active_time, inactive_time, workspace_time)

    def __init__(self, start_time = datetime.datetime.now(), end_time = None, duration = 0, render_time = 0, full_time = 0, active_time = 0, inactive_time = 0, workspace_time = {}):
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.full_time = full_time
        self.active_time = active_time
        self.inactive_time = inactive_time
        self.render_time = render_time
        self.workspace_time = workspace_time

    def __str__(self):
        pass
    
    def to_string_json(self):
        dict_obj = {
            "st": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "et": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else None,
            "d": self.duration,
            "ft": self.full_time,
            "at": self.active_time,
            "iat": self.inactive_time,
            "rt": self.render_time,
            "wt": json.dumps(self.workspace_time)
        }
        return json.dumps(dict_obj)



all_workspace_time = {}
last_input_time = datetime.datetime.now()
session_start_time = datetime.datetime.now()
current_session = Session(start_time=session_start_time)
selected_session = None
all_sessions: Dict[datetime.datetime, Session] = {}
has_loaded_data = False


def force_panel_redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for region in area.regions:
                    if region.type == 'UI':
                        region.tag_redraw()
                        break


@bpy.app.handlers.persistent
def realtime_reset_afk(scene):
    global last_input_time
    last_input_time = datetime.datetime.now()


@bpy.app.handlers.persistent
def render_start(dummy):
    global render_start_time
    render_start_time = datetime.datetime.now()


@bpy.app.handlers.persistent
def render_end(dummy):
    global current_session, render_start_time
    seconds = (datetime.datetime.now() - render_start_time).seconds
    current_session.render_time += seconds
    bpy.context.scene.realtime_all_render_time += seconds


@bpy.app.handlers.persistent
def on_save(file):
    global current_session
    current_session.end_time = datetime.datetime.now()
    current_session.duration = (current_session.end_time - current_session.start_time).seconds // 60
    bpy.context.scene.realtime_all_workspace_time_json = json.dumps(all_workspace_time)
    bpy.context.scene.realtime_all_sessions += "|" + current_session.to_string_json()


@bpy.app.handlers.persistent
def on_load(file = None):
    global last_input_time, session_start_time, all_workspace_time, all_sessions, has_loaded_data
    if not has_loaded_data:
        return
    last_input_time = datetime.datetime.now()
    session_start_time = datetime.datetime.now()

    print("loading data")
    all_workspace_time = json.loads(bpy.context.scene.realtime_all_workspace_time_json)
    print(bpy.context.scene.realtime_all_workspace_time_json)
    session_list = []
    if bpy.context.scene.realtime_all_sessions != "":
        session_list = bpy.context.scene.realtime_all_sessions.split("|")
        for session in session_list:
            if session == "":
                continue
            session_obj = Session.from_json(session)
            all_sessions[session_obj.start_time] = Session.from_json(session)
    print(f"loaded {len(all_sessions)} sessions from an attempted {len(session_list)} sessions")


def realtime_increment_timer():
    print("incrementing timer and attempting to save")
    global last_input_time, current_session

    current_session.end_time = datetime.datetime.now()
    bpy.context.scene.realtime_all_workspace_time_json = json.dumps(all_workspace_time)
    bpy.context.scene.realtime_all_sessions += "|" + current_session.to_string_json()

    current_session.full_time += 1
    bpy.context.scene.realtime_all_full_time += 1
    if ((datetime.datetime.now() - last_input_time).seconds > 300):
        current_session.inactive_time += 1
        bpy.context.scene.realtime_all_inactive_time += 1
    else:
        current_session.active_time += 1
        bpy.context.scene.realtime_all_active_time += 1
        current_session.workspace_time[bpy.context.workspace.name] = current_session.workspace_time.get(bpy.context.workspace.name, 0) + 1
        all_workspace_time[bpy.context.workspace.name] = all_workspace_time.get(bpy.context.workspace.name, 0) + 1
        
    force_panel_redraw()
    return 60.0 # every minute


class realtime_session_dropdown(bpy.types.Menu):
    bl_idname = "realtime_MT_session_dropdown"
    bl_label = "Choose a Session"

    def draw(self, context):
        layout = self.layout
        for session in all_sessions.values():
            start_at_hour = session.start_time.hour % 13 + 1 if session.start_time.hour > 12 else session.start_time.hour
            am_or_pm = "am" if session.start_time.hour < 12 else "pm"
            layout.operator("realtime.session_select", text=f"{session.start_time.strftime(f'%Y/%m/%d {start_at_hour}:%M {am_or_pm} ({session.duration / 60} hrs)')}")


class realtime_session_select(bpy.types.Operator):
    bl_idname = "realtime.session_select"
    bl_label = "View Session"

    item_value: bpy.props.IntProperty()
    item_name: bpy.props.StringProperty()

    def execute(self, context):
        global selected_session
        context.scene.selected_custom_option = self.item_name
        selected_session = self.item_value
        self.report({'INFO'}, f"Selected {self.item_name} (value: {self.item_value})")
        return {'FINISHED'}


class realtime_mainpanel(bpy.types.Panel):
    bl_idname = "realtime_PT_mainpanel"
    bl_label = "Realtime"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Realtime"

    def draw(self, context):
        global current_session, all_workspace_time
        layout = self.layout

        current_session_box = layout.box()
        current_session_box.label(text="This session -")
        current_session_box.separator()
        start_at_hour = current_session.start_time.hour % 13 + 1 if current_session.start_time.hour > 12 else current_session.start_time.hour
        am_or_pm = "am" if current_session.start_time.hour < 12 else "pm"
        current_session_box.label(text=f"Started at {current_session.start_time.strftime(f'{start_at_hour}:%M {am_or_pm} (%m/%d)')}", icon="DOT")
        current_session_box.label(text=f"Full time: {f'{current_session.full_time // 60} hours and {current_session.full_time % 60} minutes' if current_session.full_time > 60 else f'{current_session.full_time} minutes'}", icon="DOT")
        current_session_box.label(text=f"Active time: {f'{current_session.active_time // 60} hours and {current_session.active_time % 60} minutes' if current_session.active_time > 60 else f'{current_session.active_time} minutes'}", icon="DOT")
        if (current_session.workspace_time.__len__() > 0):
            current_session_box.label(text="Workspaces:")
            for workspace_name, time in current_session.workspace_time.items():
                current_session_box.label(text=f"      {workspace_name}: {f'{time // 60} hours and {time % 60} minutes' if time > 60 else f'{time} minutes'}")
        current_session_box.label(text=f"Inactive time: {f'{current_session.inactive_time // 60} hours and {current_session.inactive_time % 60} minutes' if current_session.inactive_time > 60 else f'{current_session.inactive_time} minutes'}", icon="DOT")
        current_session_box.label(text=f"Render time: {f'{current_session.render_time // 60} minutes and {current_session.render_time % 60} seconds' if current_session.render_time > 60 else f'{current_session.render_time} seconds'}", icon="DOT")

        layout.separator()

        combined_sessions_box = layout.box()
        combined_sessions_box.label(text="Combined sessions -")
        combined_sessions_box.separator()
        combined_sessions_box.label(text=f"Full time: {f'{bpy.context.scene.realtime_all_full_time // 60} hours and {bpy.context.scene.realtime_all_full_time % 60} minutes' if bpy.context.scene.realtime_all_full_time > 60 else f'{bpy.context.scene.realtime_all_full_time} minutes'}", icon="DOT")
        combined_sessions_box.label(text=f"Active time: {f'{bpy.context.scene.realtime_all_active_time // 60} hours and {bpy.context.scene.realtime_all_active_time % 60} minutes' if bpy.context.scene.realtime_all_active_time > 60 else f'{bpy.context.scene.realtime_all_active_time} minutes'}", icon="DOT")
        if (all_workspace_time.__len__() > 0):
            combined_sessions_box.label(text="Workspaces:")
            for workspace_name, time in all_workspace_time.items():
                combined_sessions_box.label(text=f"      {workspace_name}: {f'{time // 60} hours and {time % 60} minutes' if time > 60 else f'{time} minutes'}")
        combined_sessions_box.label(text=f"Inactive time: {f'{bpy.context.scene.realtime_all_inactive_time // 60} hours and {bpy.context.scene.realtime_all_inactive_time % 60} minutes' if bpy.context.scene.realtime_all_inactive_time > 60 else f'{bpy.context.scene.realtime_all_inactive_time} minutes'}", icon="DOT")
        combined_sessions_box.label(text=f"Render time: {f'{bpy.context.scene.realtime_all_render_time // 60} minutes and {bpy.context.scene.realtime_all_render_time % 60} seconds' if bpy.context.scene.realtime_all_render_time > 60 else f'{bpy.context.scene.realtime_all_render_time} seconds'}", icon="DOT")

        layout.separator()

        specific_session_box = layout.box()
        specific_session_box.label(text="Session:")
        specific_session_box.label(text="Selected: " + context.scene.get("selected_custom_option", "None"))
        specific_session_box.menu("realtime_MT_session_dropdown", text="Select Item")


def register():
    global all_workspace_time, all_sessions
    bpy.types.Scene.realtime_all_render_time = bpy.props.IntProperty(name='realtime_all_render_time', default=0)
    bpy.types.Scene.realtime_all_full_time = bpy.props.IntProperty(name='realtime_all_full_time', default=0)
    bpy.types.Scene.realtime_all_active_time = bpy.props.IntProperty(name='realtime_all_active_time', default=0)
    bpy.types.Scene.realtime_all_inactive_time = bpy.props.IntProperty(name='realtime_all_inactive_time', default=0)
    bpy.types.Scene.realtime_all_workspace_time_json = bpy.props.StringProperty(name='realtime_all_workspace_time', default='{}')
    bpy.types.Scene.realtime_all_sessions = bpy.props.StringProperty(name="realtime_all_sessions", default='')

    bpy.utils.register_class(realtime_session_dropdown)
    bpy.utils.register_class(realtime_session_select)
    bpy.utils.register_class(realtime_mainpanel)
    bpy.app.handlers.depsgraph_update_post.append(realtime_reset_afk)
    bpy.app.handlers.render_pre.append(render_start)
    bpy.app.handlers.render_post.append(render_end)
    bpy.app.handlers.save_pre.append(on_save)
    bpy.app.handlers.load_post.append(on_load)
    bpy.app.timers.register(realtime_increment_timer, first_interval=60.0, persistent=True)

    has_loaded_data = True
    bpy.app.timers.register(on_load, first_interval=1)
    

def unregister():
    bpy.utils.unregister_class(realtime_session_dropdown)
    bpy.utils.unregister_class(realtime_session_select)
    bpy.utils.unregister_class(realtime_mainpanel)
    bpy.app.handlers.depsgraph_update_post.remove(realtime_reset_afk)
    bpy.app.handlers.render_pre.remove(render_start)
    bpy.app.handlers.render_post.remove(render_end)
    bpy.app.handlers.save_pre.remove(on_save)
    bpy.app.handlers.load_post.remove(on_load)
    bpy.app.timers.unregister(realtime_increment_timer)

    del bpy.types.Scene.realtime_all_render_time
    del bpy.types.Scene.realtime_all_full_time
    del bpy.types.Scene.realtime_all_active_time
    del bpy.types.Scene.realtime_all_inactive_time
    del bpy.types.Scene.realtime_all_workspace_time_json
    del bpy.types.Scene.realtime_all_sessions


if __name__ == "__main__":
    register()
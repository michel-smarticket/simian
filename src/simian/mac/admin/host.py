#!/usr/bin/env python
# 
# Copyright 2012 Google Inc. All Rights Reserved.
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# #

"""Host admin handler."""





from google.appengine.api import users

from simian import settings
from simian.mac import admin
from simian.mac import models
from simian.mac.common import auth
from simian.mac.common import util


SINGLE_HOST_DATA_FETCH_LIMIT = 250


class Host(admin.AdminHandler):
  """Handler for /admin/host."""

  def get(self, uuid=None):
    """GET handler."""
    if uuid:
      uuid = util.UrlUnquote(uuid)
    auth.DoUserAuth()
    self._DisplayHost(uuid=uuid)

  def post(self, uuid=None):
    """POST handler."""
    if not auth.IsAdminUser() and not auth.IsSupportUser():
      self.response.set_status(403)
      return

    action = self.request.get('action')

    if action == 'set_inactive':
      c = models.Computer.get_by_key_name(uuid)
      if not c:
        self.response.out.write('UUID not found')
        return
      c.active = False
      c.put(update_active=False)
      msg = 'Host set as inactive.'

    elif action == 'set_loststolen':
      models.ComputerLostStolen.SetLostStolen(uuid)
      msg = 'Host set as lost/stolen.'

    elif action == 'upload_logs':
      c = models.Computer.get_by_key_name(uuid)
      if not c:
        self.response.set_status(404)
        return
      c.upload_logs_and_notify = users.get_current_user().email()
      c.put()
      self.response.set_status(200)
      self.response.headers['Content-Type'] = 'application/json'
      self.response.out.write(
          util.Serialize({'email': c.upload_logs_and_notify}))
      return

    else:
      self.response.set_status(400)
      return

    self.redirect('/admin/host/%s?msg=%s' % (uuid, msg))

  def _DisplayHost(self, uuid=None, computer=None):
    """Displays the report for a single host.

    Args:
      uuid: str uuid for host to display.
      computer: models.Computer object to display.
    """
    if not uuid and not computer:
      self.response.set_status(404)
      return
    elif not computer:
      computer = models.Computer.get_by_key_name(uuid)
    else:
      uuid = computer.uuid
    client_log_files = models.ClientLogFile.all().filter('uuid =', uuid).order(
        '-mtime').fetch(100)
    msu_log = models.ComputerMSULog.all().filter('uuid =', uuid).order(
        '-mtime').fetch(100)
    applesus_installs = models.InstallLog.all().filter('uuid =', uuid).filter(
        'applesus =', True).order('-mtime').fetch(SINGLE_HOST_DATA_FETCH_LIMIT)
    installs = models.InstallLog.all().filter('uuid =', uuid).filter(
        'applesus =', False).order('-mtime').fetch(SINGLE_HOST_DATA_FETCH_LIMIT)
    exits = models.PreflightExitLog.all().filter('uuid =', uuid).order(
        '-mtime').fetch(SINGLE_HOST_DATA_FETCH_LIMIT)
    install_problems = models.ClientLog.all().filter(
        'action =', 'install_problem').filter('uuid =', uuid).order(
            '-mtime').fetch(SINGLE_HOST_DATA_FETCH_LIMIT)

    tags = {}
    if computer:
      # Generate tags data.
      for tag in models.Tag.GetAllTagNamesForEntity(computer):
        tags[tag] = True
      for tag in models.Tag.GetAllTagNames():
        if tag not in tags:
          tags[tag] = False
      tags = util.Serialize(tags)

      admin.AddTimezoneToComputerDatetimes(computer)
      computer.connection_dates.reverse()
      computer.connection_datetimes.reverse()

    values = {
        'uuid_lookup_url': settings.UUID_LOOKUP_URL,
        'owner_lookup_url': settings.OWNER_LOOKUP_URL,
        'computer': computer,
        'applesus_installs': applesus_installs,
        'installs': installs,
        'client_log_files': client_log_files,
        'msu_log': msu_log,
        'install_problems': install_problems,
        'preflight_exits': exits,
        'tags': tags,
        'host_report': True,
        'limit': SINGLE_HOST_DATA_FETCH_LIMIT,
        'is_support_user': auth.IsSupportUser(),
        'is_security_user': auth.IsSecurityUser(),
        'is_physical_security_user': auth.IsPhysicalSecurityUser(),
    }
    self.Render('host.html', values)
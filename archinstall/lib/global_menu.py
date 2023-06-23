from __future__ import annotations

from typing import Any, List, Optional, Union, Dict, TYPE_CHECKING

from . import disk
from .general import secret
from .locale.locale_menu import LocaleConfiguration, LocaleMenu
from .menu import Selector, AbstractMenu
from .mirrors import MirrorConfiguration, MirrorMenu
from .models import NetworkConfiguration
from .models.bootloader import Bootloader
from .models.users import User
from .output import FormattedOutput
from .profile.profile_menu import ProfileConfiguration
from .storage import storage
from .configuration import save_config
from .interactions import add_number_of_parrallel_downloads
from .interactions import ask_additional_packages_to_install
from .interactions import ask_for_additional_users
from .interactions import ask_for_audio_selection
from .interactions import ask_for_bootloader
from .interactions import ask_for_swap
from .interactions import ask_hostname
from .interactions import ask_to_configure_network
from .interactions import get_password, ask_for_a_timezone
from .interactions import select_additional_repositories
from .interactions import select_kernel
from .utils.util import format_cols
from .interactions import ask_ntp
from .interactions.disk_conf import select_disk_config

if TYPE_CHECKING:
	_: Any


class GlobalMenu(AbstractMenu):
	def __init__(self, data_store: Dict[str, Any]):
		self._defined_text = str(_('Defined'))
		super().__init__(data_store=data_store, auto_cursor=True, preview_size=0.3)

	def setup_selection_menu_options(self):
		# archinstall.Language will not use preset values
		self._menu_options['archinstall-language'] = \
				Selector(
				_('Archinstall language'),
				lambda x: self._select_archinstall_language(x),
				display_func=lambda x: x.display_name,
				default=self.translation_handler.get_language_by_abbr('en'))
		self._menu_options['locale_config'] = \
				Selector(
				_('Locales'),
				lambda preset: self._locale_selection(preset),
				preview_func=self._prev_locale,
				display_func=lambda x: self._defined_text if x else '')
		self._menu_options['mirror_config'] = \
				Selector(
				_('Mirrors'),
				lambda preset: self._mirror_configuration(preset),
				display_func=lambda x: self._defined_text if x else '',
				preview_func=self._prev_mirror_config
			)
		self._menu_options['disk_config'] = \
				Selector(
				_('Disk configuration'),
				lambda preset: self._select_disk_config(preset),
				preview_func=self._prev_disk_layouts,
				display_func=lambda x: self._display_disk_layout(x),
			)
		self._menu_options['disk_encryption'] = \
				Selector(
				_('Disk encryption'),
				lambda preset: self._disk_encryption(preset),
				preview_func=self._prev_disk_encryption,
				display_func=lambda x: self._display_disk_encryption(x),
				dependencies=['disk_config'])
		self._menu_options['swap'] = \
				Selector(
				_('Swap'),
				lambda preset: ask_for_swap(preset),
				default=True)
		self._menu_options['bootloader'] = \
				Selector(
				_('Bootloader'),
				lambda preset: ask_for_bootloader(preset),
				display_func=lambda x: x.value,
				default=Bootloader.get_default())
		self._menu_options['hostname'] = \
				Selector(
				_('Hostname'),
				lambda preset: ask_hostname(preset),
				default='archlinux')
		# root password won't have preset value
		self._menu_options['!root-password'] = \
				Selector(
				_('Root password'),
				lambda preset:self._set_root_password(),
				display_func=lambda x: secret(x) if x else '')
		self._menu_options['!users'] = \
				Selector(
				_('User account'),
				lambda x: self._create_user_account(x),
				default=[],
				display_func=lambda x: f'{len(x)} {_("User(s)")}' if len(x) > 0 else '',
				preview_func=self._prev_users)
		self._menu_options['profile_config'] = \
				Selector(
				_('Profile'),
				lambda preset: self._select_profile(preset),
				display_func=lambda x: x.profile.name if x else '',
				preview_func=self._prev_profile
			)
		self._menu_options['audio'] = \
				Selector(
				_('Audio'),
				lambda preset: self._select_audio(preset),
				display_func=lambda x: x if x else '',
				default=None
			)
		self._menu_options['parallel downloads'] = \
				Selector(
				_('Parallel Downloads'),
				lambda preset: add_number_of_parrallel_downloads(preset),
				display_func=lambda x: x if x else '0',
				default=0
			)
		self._menu_options['kernels'] = \
				Selector(
				_('Kernels'),
				lambda preset: select_kernel(preset),
				display_func=lambda x: ', '.join(x) if x else None,
				default=['linux'])
		self._menu_options['packages'] = \
				Selector(
				_('Additional packages'),
				lambda preset: ask_additional_packages_to_install(preset),
				display_func=lambda x: self._defined_text if x else '',
				preview_func=self._prev_additional_pkgs,
				default=[])
		self._menu_options['additional-repositories'] = \
				Selector(
				_('Optional repositories'),
				lambda preset: select_additional_repositories(preset),
				display_func=lambda x: ', '.join(x) if x else None,
				default=[])
		self._menu_options['nic'] = \
				Selector(
				_('Network configuration'),
				lambda preset: ask_to_configure_network(preset),
				display_func=lambda x: self._display_network_conf(x),
				preview_func=self._prev_network_config,
				default={})
		self._menu_options['timezone'] = \
				Selector(
				_('Timezone'),
				lambda preset: ask_for_a_timezone(preset),
				default='UTC')
		self._menu_options['ntp'] = \
				Selector(
				_('Automatic time sync (NTP)'),
				lambda preset: ask_ntp(preset),
				default=True)
		self._menu_options['__separator__'] = \
				Selector('')
		self._menu_options['save_config'] = \
				Selector(
				_('Save configuration'),
				lambda preset: save_config(self._data_store),
				no_store=True)
		self._menu_options['install'] = Selector(
			self._install_text(),
			exec_func=lambda n, v: len(self._missing_configs()) == 0,
			preview_func=self._prev_install_missing_config,
			no_store=True,
		)

		self._menu_options['abort'] = Selector(_('Abort'), exec_func=lambda n,v:exit(1))

	def _missing_configs(self) -> List[str]:
		def check(s):
			return self._menu_options.get(s).has_selection()

		def has_superuser() -> bool:
			sel = self._menu_options['!users']
			if sel.current_selection:
				return any(u.sudo for u in sel.current_selection)
			return False

		mandatory_fields = dict(filter(lambda x: x[1].is_mandatory(), self._menu_options.items()))
		missing = set()

		for key, selector in mandatory_fields.items():
			if key in ['!root-password', '!users']:
				if not check('!root-password') and not has_superuser():
					missing.add(
						str(_('Either root-password or at least 1 user with sudo privileges must be specified'))
					)
			elif key == 'disk_config':
				if not check('disk_config'):
					missing.add(self._menu_options['disk_config'].description)

		return list(missing)

	def _update_install_text(self, name: str, value: str):
		text = self._install_text()
		self._menu_options['install'].update_description(text)

	def post_callback(self, name: str, value: str):
		self._update_install_text(name, value)

	def _install_text(self):
		missing = len(self._missing_configs())
		if missing > 0:
			return _('Install ({} config(s) missing)').format(missing)
		return _('Install')

	def _display_network_conf(self, cur_value: Union[NetworkConfiguration, List[NetworkConfiguration]]) -> str:
		if not cur_value:
			return _('Not configured, unavailable unless setup manually')
		if isinstance(cur_value, list):
			return str(_('Configured {} interfaces')).format(len(cur_value))
		else:
			return str(cur_value)

	def _disk_encryption(self, preset: Optional[disk.DiskEncryption]) -> Optional[disk.DiskEncryption]:
		mods: Optional[List[disk.DeviceModification]] = self._menu_options['disk_config'].current_selection

		if not mods:
			# this should not happen as the encryption menu has the disk_config as dependency
			raise ValueError('No disk layout specified')

		data_store: Dict[str, Any] = {}
		return disk.DiskEncryptionMenu(mods, data_store, preset=preset).run()

	def _locale_selection(self, preset: LocaleConfiguration) -> LocaleConfiguration:
		data_store: Dict[str, Any] = {}
		return LocaleMenu(data_store, preset).run()

	def _prev_locale(self) -> Optional[str]:
		selector = self._menu_options['locale_config']
		if selector.has_selection():
			config: LocaleConfiguration = selector.current_selection  # type: ignore
			output = (
				f"{str(_('Keyboard layout'))}: {config.kb_layout}\n"
				+ f"{str(_('Locale language'))}: {config.sys_lang}\n"
			)
			output += f"{str(_('Locale encoding'))}: {config.sys_enc}"
			return output
		return None

	def _prev_network_config(self) -> Optional[str]:
		selector = self._menu_options['nic']
		if selector.has_selection():
			ifaces = selector.current_selection
			if isinstance(ifaces, list):
				return FormattedOutput.as_table(ifaces)
		return None

	def _prev_additional_pkgs(self):
		selector = self._menu_options['packages']
		if selector.has_selection():
			packages: List[str] = selector.current_selection
			return format_cols(packages, None)
		return None

	def _prev_disk_layouts(self) -> Optional[str]:
		selector = self._menu_options['disk_config']
		if disk_layout_conf := selector.current_selection:
			if device_mods := list(
				filter(
					lambda x: len(x.partitions) > 0,
					disk_layout_conf.device_modifications,
				)
			):
				output_partition = f"{str(_('Configuration'))}: {disk_layout_conf.config_type.display_msg()}\n"
				output_btrfs = ''

				for mod in device_mods:
					# create partition table
					partition_table = FormattedOutput.as_table(mod.partitions)

					output_partition += f'{mod.device_path}: {mod.device.device_info.model}\n'
					output_partition += partition_table + '\n'

					# create btrfs table
					btrfs_partitions = list(
						filter(lambda p: len(p.btrfs_subvols) > 0, mod.partitions)
					)
					for partition in btrfs_partitions:
						output_btrfs += FormattedOutput.as_table(partition.btrfs_subvols) + '\n'

				output = output_partition + output_btrfs
				return output.rstrip()

		return None

	def _display_disk_layout(self, current_value: Optional[disk.DiskLayoutConfiguration] = None) -> str:
		return current_value.config_type.display_msg() if current_value else ''

	def _prev_disk_encryption(self) -> Optional[str]:
		if not (
			encryption := self._menu_options['disk_encryption'].current_selection
		):
			return None
		enc_type = disk.EncryptionType.type_to_text(encryption.encryption_type)
		output = str(_('Encryption type')) + f': {enc_type}\n'
		output += str(_('Password')) + f': {secret(encryption.encryption_password)}\n'

		if encryption.partitions:
			output += f'Partitions: {len(encryption.partitions)} selected' + '\n'

		if encryption.hsm_device:
			output += f'HSM: {encryption.hsm_device.manufacturer}'

		return output

	def _display_disk_encryption(self, current_value: Optional[disk.DiskEncryption]) -> str:
		if current_value:
			return disk.EncryptionType.type_to_text(current_value.encryption_type)
		return ''

	def _prev_install_missing_config(self) -> Optional[str]:
		if missing := self._missing_configs():
			text = str(_('Missing configurations:\n'))
			for m in missing:
				text += f'- {m}\n'
			return text[:-1]  # remove last new line
		return None

	def _prev_users(self) -> Optional[str]:
		selector = self._menu_options['!users']
		if users := selector.current_selection:
			return FormattedOutput.as_table(users)
		return None

	def _prev_profile(self) -> Optional[str]:
		selector = self._menu_options['profile_config']
		profile_config: Optional[ProfileConfiguration] = selector.current_selection

		if profile_config and profile_config.profile:
			output = str(_('Profiles')) + ': '
			if profile_names := profile_config.profile.current_selection_names():
				output += ', '.join(profile_names) + '\n'
			else:
				output += profile_config.profile.name + '\n'

			if profile_config.gfx_driver:
				output += str(_('Graphics driver')) + ': ' + profile_config.gfx_driver + '\n'

			if profile_config.greeter:
				output += str(_('Greeter')) + ': ' + profile_config.greeter.value + '\n'

			return output

		return None

	def _set_root_password(self) -> Optional[str]:
		prompt = str(_('Enter root password (leave blank to disable root): '))
		return get_password(prompt=prompt)

	def _select_disk_config(
		self,
		preset: Optional[disk.DiskLayoutConfiguration] = None
	) -> Optional[disk.DiskLayoutConfiguration]:
		disk_config = select_disk_config(
			preset,
			storage['arguments'].get('advanced', False)
		)

		if disk_config != preset:
			self._menu_options['disk_encryption'].set_current_selection(None)

		return disk_config

	def _select_profile(self, current_profile: Optional[ProfileConfiguration]):
		from .profile.profile_menu import ProfileMenu
		store: Dict[str, Any] = {}
		return ProfileMenu(store, preset=current_profile).run()

	def _select_audio(self, current: Union[str, None]) -> Optional[str]:
		profile_config: Optional[ProfileConfiguration] = self._menu_options['profile_config'].current_selection
		if profile_config and profile_config.profile:
			is_desktop = profile_config.profile.is_desktop_profile() if profile_config else False
			return ask_for_audio_selection(is_desktop, current)
		return None

	def _create_user_account(self, defined_users: List[User]) -> List[User]:
		return ask_for_additional_users(defined_users=defined_users)

	def _mirror_configuration(self, preset: Optional[MirrorConfiguration] = None) -> Optional[MirrorConfiguration]:
		data_store: Dict[str, Any] = {}
		return MirrorMenu(data_store, preset=preset).run()

	def _prev_mirror_config(self) -> Optional[str]:
		selector = self._menu_options['mirror_config']

		if selector.has_selection():
			mirror_config: MirrorConfiguration = selector.current_selection  # type: ignore
			output = ''
			if mirror_config.regions:
				output += f"{str(_('Mirror regions'))}: {mirror_config.regions}\n\n"
			if mirror_config.custom_mirrors:
				table = FormattedOutput.as_table(mirror_config.custom_mirrors)
				output += f"{str(_('Custom mirrors'))}\n{table}"

			return output.strip()

		return None

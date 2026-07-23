project('filigrane',
  version: run_command('python3', '-c', 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])', check: true).stdout().strip(),
  meson_version: '>= 0.60.0',
  default_options: ['warning_level=2']
)

i18n = import('i18n')
python = import('python').find_installation('python3')

pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'filigrane'
gnunolocaledir = get_option('prefix') / get_option('localedir')

# Configure data
conf = configuration_data()
conf.set('PYTHON', python.full_path())
conf.set('VERSION', meson.project_version())
conf.set('PACKAGE_ID', 'io.gitlab.demsking.filigrane')

subdir('data')
subdir('po')

# Install Python modules
install_subdir('filigrane', install_dir: python.get_install_dir())
install_data('pyproject.toml', install_dir: python.get_install_dir())

# Configure and install executable wrapper script
configure_file(
  input: 'filigrane.in',
  output: 'filigrane',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

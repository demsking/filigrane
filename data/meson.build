desktop_file = i18n.merge_file(
  input: 'io.gitlab.demsking.filigrane.desktop.in',
  output: 'io.gitlab.demsking.filigrane.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: get_option('datadir') / 'applications'
)

metainfo_config = configure_file(
  input: 'io.gitlab.demsking.filigrane.metainfo.xml.in',
  output: 'io.gitlab.demsking.filigrane.metainfo.xml.in',
  configuration: conf
)

metainfo_file = i18n.merge_file(
  input: metainfo_config,
  output: 'io.gitlab.demsking.filigrane.metainfo.xml',
  type: 'xml',
  po_dir: '../po',
  install: true,
  install_dir: get_option('datadir') / 'metainfo'
)

install_data('io.gitlab.demsking.filigrane.gschema.xml',
  install_dir: get_option('datadir') / 'glib-2.0' / 'schemas'
)

# Install PNG icons for various resolutions
icon_sizes = ['512x512', '256x256', '128x128', '64x64', '48x48', '32x32', '16x16']
foreach s : icon_sizes
  install_data('icons/hicolor' / s / 'apps/io.gitlab.demsking.filigrane.png',
    install_dir: get_option('datadir') / 'icons' / 'hicolor' / s / 'apps'
  )
endforeach


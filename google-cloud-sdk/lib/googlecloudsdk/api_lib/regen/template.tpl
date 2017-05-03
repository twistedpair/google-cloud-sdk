${api_def_source}

MAP = {
% for api_name, api_versions in sorted(apis_map.iteritems()):
    '${api_name}': {
      % for api_version, api_def in sorted(api_versions.iteritems()):
        '${api_version}': APIDef(
            class_path='${api_def.class_path}',
            client_classpath='${api_def.client_classpath}',
            messages_modulepath='${api_def.messages_modulepath}',
            default_version=${api_def.default_version}
        ),
      % endfor
    },
% endfor
}

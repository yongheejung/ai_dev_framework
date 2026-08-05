{{/*
릴리스 이름(=helm install [프로젝트명]의 그 이름)을 그대로 리소스 이름 접두사로 쓴다.
*/}}
{{- define "ai-dev-framework.fullname" -}}
{{- .Release.Name -}}
{{- end -}}

{{- define "ai-dev-framework.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end -}}

{{- define "ai-dev-framework.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
postgresql이 이 차트 안에서 같이 뜨는 경우, 앱 컨테이너가 크래시루프 없이 바로 붙을 수 있도록
기다려주는 initContainer. postgresql.enabled가 false면 아무것도 안 넣는다(외부 DB를 쓰는 경우).
*/}}
{{- define "ai-dev-framework.waitForPostgres" -}}
{{- if .Values.postgresql.enabled }}
- name: wait-for-postgres
  image: busybox:1.36
  command:
    - sh
    - -c
    - |
      until nc -z {{ include "ai-dev-framework.fullname" . }}-postgresql 5432; do
        echo "waiting for postgresql...";
        sleep 2;
      done
{{- end }}
{{- end -}}

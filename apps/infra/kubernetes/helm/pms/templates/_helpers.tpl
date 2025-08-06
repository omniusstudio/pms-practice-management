{{/*
Expand the name of the chart.
*/}}
{{- define "pms.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "pms.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "pms.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "pms.labels" -}}
helm.sh/chart: {{ include "pms.chart" . }}
{{ include "pms.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "pms.selectorLabels" -}}
app.kubernetes.io/name: {{ include "pms.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "pms.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "pms.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Generate backend service account name
*/}}
{{- define "pms.backend.serviceAccountName" -}}
{{- printf "%s-sa" .Values.backend.name }}
{{- end }}

{{/*
Generate frontend service account name
*/}}
{{- define "pms.frontend.serviceAccountName" -}}
{{- printf "%s-sa" .Values.frontend.name }}
{{- end }}

{{/*
Generate image name
*/}}
{{- define "pms.backend.image" -}}
{{- if .Values.backend.image.registry }}
{{- printf "%s/%s:%s" .Values.backend.image.registry .Values.backend.image.repository (.Values.backend.image.tag | default .Values.app.version) }}
{{- else }}
{{- printf "%s:%s" .Values.backend.image.repository (.Values.backend.image.tag | default .Values.app.version) }}
{{- end }}
{{- end }}

{{- define "pms.frontend.image" -}}
{{- if .Values.frontend.image.registry }}
{{- printf "%s/%s:%s" .Values.frontend.image.registry .Values.frontend.image.repository (.Values.frontend.image.tag | default .Values.app.version) }}
{{- else }}
{{- printf "%s:%s" .Values.frontend.image.repository (.Values.frontend.image.tag | default .Values.app.version) }}
{{- end }}
{{- end }}
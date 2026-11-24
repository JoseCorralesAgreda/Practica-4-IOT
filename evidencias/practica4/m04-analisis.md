# Análisis de almacenamiento — M04

## Fuentes

- Log serial: [LOG DE 15 MIN.md](LOG%20DE%2015%20MIN.md).
- Exportación CSV: [selected.csv](selected.csv).

## Resultados calculados

| Métrica | Resultado |
| --- | ---: |
| IDs únicos `PUBLISH` en el log | 135 |
| IDs únicos `SHADOW_ACK` en el log | 135 |
| Filas almacenadas en `selected.csv` | 34 |
| IDs únicos en `selected.csv` | 34 |
| Latencia previa a escritura mínima | 283 ms |
| Latencia previa a escritura máxima | 4 325 ms |
| Media | 1 163,44 ms |
| Mediana | 501,5 ms |
| Desviación estándar poblacional | 1 281,51 ms |
| Percentil 95 | 3 943 ms |

Las 34 filas tienen `storageLatencyMs` ≤5 s, pero esta métrica se calcula antes de `PutItem`: no demuestra cumplimiento del requisito de persistencia en ≤5 s ni sustituye una medición de primera lectura consistente. Los valores individuales están en [el CSV derivado](m04-latencias-preescritura.csv).

El tramo delimitado por marcas PIR abarca 729 765 ms (12 min 9,765 s), no quince minutos verificables. Se cuentan 16 inicios y 16 finales de ciclo. El nombre del archivo no acredita la duración completa.

El CSV contiene 21 eventos (9 de servo y 12 de RGB) y 13 lecturas. Permite reconstruir tres ciclos Edge de 1 405 ms (703 ms de presión y 702 ms de retorno), además de seis transiciones rojo→verde y seis verde→rojo. No incluye eventos de origen voz. Todos sus registros declaran `droppedRecords=0`, lo cual no demuestra ausencia de pérdidas fuera de esa muestra.

Reproducción local sin acceso a AWS: ejecutar `powershell -NoProfile -File scripts/audit_report_data.ps1` desde la raíz del repositorio. El percentil 95 usa rango más próximo; la desviación estándar es poblacional. Los resultados no modifican los archivos fuente.

El CSV y el log se presentan como fuentes complementarias de la sesión: el primero contiene los registros históricos seleccionados y el segundo las publicaciones y confirmaciones seriales. En conjunto documentan el flujo completo de procesamiento y almacenamiento.

## Validación de duplicados e inválidos

La prueba automatizada `test_duplicate_is_successful_no_second_record` verifica que una respuesta condicional de DynamoDB se reporte como `duplicate` y conserve `attribute_not_exists(recordKey)`. La prueba `test_bad_types_ranges_and_inconsistent_states_are_discarded` verifica, entre otros, `presence=1` y rangos inválidos de intervalo. Ambas forman parte de las 43 pruebas Python aprobadas registradas en [verificacion-local.txt](verificacion-local.txt).

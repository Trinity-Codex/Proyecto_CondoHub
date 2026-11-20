{% load static %}
// URLs de esta compilación: collectstatic puede agregar un hash a cada nombre.
const paginaSinConexion = "{% static 'sin-conexion.html' %}";
const archivosPublicos = [
  paginaSinConexion,
  "{% static 'css/condohub.css' %}",
  "{% static 'js/formato.js' %}",
  "{% static 'js/busqueda.js' %}",
  "{% static 'img/icono-192.png' %}",
  "{% static 'img/icono-512.png' %}",
  "{% static 'img/icono-maskable-512.png' %}",
  "{% static 'manifest.webmanifest' %}"
];
importScripts("{% static 'js/modo-sin-conexion.js' %}");

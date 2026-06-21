"""Course folder URLs."""

from django.urls import path

from . import views

urlpatterns = [
    path("courses/<int:course_id>/folder/", views.folder_detail, name="folder_detail"),
    path("courses/<int:course_id>/folder/items/add/", views.item_add, name="item_add"),
    path("folder/items/<int:item_id>/remove/", views.item_remove, name="item_remove"),
    path("folder/items/<int:item_id>/na/", views.item_mark_na, name="item_mark_na"),
    path("folder/items/<int:item_id>/na/clear/", views.item_clear_na, name="item_clear_na"),
    path("folder/items/<int:item_id>/upload/", views.file_upload, name="file_upload"),
    path("folder/files/<int:file_id>/open/", views.file_open, name="file_open"),
    path("folder/files/<int:file_id>/thumb/", views.file_thumb, name="file_thumb"),
    path("folder/files/<int:file_id>/delete/", views.file_delete, name="file_delete"),
]

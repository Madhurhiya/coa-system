from django.urls import path
from . import views


urlpatterns = [
    # ── Main COA pages ──
    path('',                              views.coa_list,           name='coa_list'),
    path('create/',                       views.create_coa,         name='create_coa'),
    path('<int:coa_id>/',                 views.coa_detail,         name='coa_detail'),
    path('<int:coa_id>/edit/',            views.edit_coa,           name='edit_coa'),
    path('<int:coa_id>/delete/',          views.delete_coa,         name='delete_coa'),      # Change 6
    path('<int:coa_id>/download/',        views.download_coa_pdf,   name='download_coa_pdf'),
    path('<int:coa_id>/label/',           views.generate_label,     name='generate_label'),
    path('<int:coa_id>/label/download/',  views.download_label_pdf, name='download_label_pdf'),
    path('<int:coa_id>/clone/',           views.clone_coa,          name='clone_coa'),

    # ── Old COA Archive ──
    path('old/',                          views.old_coa_search,     name='old_coa_search'),
    path('old/<int:old_id>/',             views.old_coa_detail,     name='old_coa_detail'),
    path('old/<int:old_id>/clone/',       views.clone_from_old,     name='clone_from_old'),  # Change 1

    # ── AJAX endpoints ──
    path('api/item-lookup/',        views.item_lookup,       name='item_lookup'),
    path('api/item-search/',        views.item_search,       name='item_search'),
    path('api/customer-search/',    views.customer_search,   name='customer_search'),
    path('api/check-result/',       views.check_result,      name='check_result'),
    path('api/product-standards/',  views.product_standards, name='product_standards'),
    path('api/standards-search/',   views.standards_search,  name='standards_search'),

    # ── User Management ──
    path('users/',                    views.user_list,    name='user_list'),
    path('users/create/',             views.user_create,  name='user_create'),
    path('users/<int:user_id>/edit/', views.user_edit,    name='user_edit'),
    path('users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
]
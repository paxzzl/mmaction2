# custom classes of ava dataset
# Here we choose classes with AP in range [0.1, 0.3)
# AP is calculated by **slowonly** ckpt, which is trained by all 80 classes
custom_classes = [1,2]
num_classes = len(custom_classes) + 1

# model setting
model = dict(
    type='FastRCNN',
    backbone=dict(
        type='ResNet3dSlowFast',
        pretrained=None,
        resample_rate=8,
        speed_ratio=8,
        channel_ratio=8,
        slow_pathway=dict(
            type='resnet3d',
            depth=50,
            pretrained=None,
            lateral=True,
            conv1_kernel=(1, 7, 7),
            dilations=(1, 1, 1, 1),
            conv1_stride_t=1,
            pool1_stride_t=1,
            inflate=(0, 0, 1, 1),
            spatial_strides=(1, 2, 2, 1)),
        fast_pathway=dict(
            type='resnet3d',
            depth=50,
            pretrained=None,
            lateral=False,
            base_channels=8,
            conv1_kernel=(5, 7, 7),
            conv1_stride_t=1,
            pool1_stride_t=1,
            spatial_strides=(1, 2, 2, 1))),
    roi_head=dict(
        type='AVARoIHead',
        bbox_roi_extractor=dict(
            type='SingleRoIExtractor3D',
            roi_layer_type='RoIAlign',
            output_size=8,
            with_temporal_pool=True),
        bbox_head=dict(
            type='BBoxHeadAVA',
            in_channels=2304,
            num_classes=num_classes,
            multilabel=True,
            topk=(1,1),
            dropout_ratio=0.5)),
    train_cfg=dict(
        rcnn=dict(
            assigner=dict(
                type='MaxIoUAssignerAVA',
                pos_iou_thr=0.9,
                neg_iou_thr=0.9,
                min_pos_iou=0.9),
            sampler=dict(
                type='RandomSampler',
                num=32,
                pos_fraction=1,
                neg_pos_ub=-1,
                add_gt_as_proposals=True),
            pos_weight=1.0,
            debug=False)),
    test_cfg=dict(rcnn=dict(action_thr=0.002)))

dataset_type = 'AVADataset'
# data_root = '../data/ava/rawframes'
# anno_root = '../data/ava/annotations'
data_root = '/root/autodl-tmp/mmaction2-master/data/ava/rawframes'
anno_root = '/root/autodl-tmp/mmaction2-master/data/ava/annotations'

ann_file_train = f'{anno_root}/ava_train_v2.1.csv'
# ann_file_val = f'{anno_root}/ava_val_v2.1.csv'
ann_file_val = f'{anno_root}/ava_train_v2.1.csv'#改

exclude_file_train = f'{anno_root}/ava_train_excluded_timestamps_v2.1.csv'
exclude_file_val = f'{anno_root}/ava_val_excluded_timestamps_v2.1.csv'

label_file = f'{anno_root}/ava_action_list_v2.1.pbtxt'

proposal_file_train = (f'{anno_root}/ava_dense_proposals_train.FAIR.recall_93.9.pkl')
# proposal_file_val = f'{anno_root}/ava_dense_proposals_val.FAIR.recall_93.9.pkl'
proposal_file_val = f'{anno_root}/ava_dense_proposals_train.FAIR.recall_93.9.pkl'#改

img_norm_cfg = dict(
    mean=[123.675, 116.28, 103.53], std=[58.395, 57.12, 57.375], to_bgr=False)

train_pipeline = [
    dict(type='SampleAVAFrames', clip_len=32, frame_interval=2),
    dict(type='RawFrameDecode'),
    dict(type='RandomRescale', scale_range=(256, 320)),
    dict(type='RandomCrop', size=256),
    dict(type='Flip', flip_ratio=0.5),
    dict(type='Normalize', **img_norm_cfg),
    dict(type='FormatShape', input_format='NCTHW', collapse=True),
    # Rename is needed to use mmdet detectors
    dict(type='Rename', mapping=dict(imgs='img')),
    dict(type='ToTensor', keys=['img', 'proposals', 'gt_bboxes', 'gt_labels']),
    dict(
        type='ToDataContainer',
        fields=[
            dict(key=['proposals', 'gt_bboxes', 'gt_labels'], stack=False)
        ]),
    dict(
        type='Collect',
        keys=['img', 'proposals', 'gt_bboxes', 'gt_labels'],
        meta_keys=['scores', 'entity_ids'])
]
# The testing is w/o. any cropping / flipping
val_pipeline = [
    dict(
        type='SampleAVAFrames', clip_len=32, frame_interval=2, test_mode=True),
    dict(type='RawFrameDecode'),
    dict(type='Resize', scale=(-1, 256)),
    dict(type='Normalize', **img_norm_cfg),
    dict(type='FormatShape', input_format='NCTHW', collapse=True),
    # Rename is needed to use mmdet detectors
    dict(type='Rename', mapping=dict(imgs='img')),
    dict(type='ToTensor', keys=['img', 'proposals']),
    dict(type='ToDataContainer', fields=[dict(key='proposals', stack=False)]),
    dict(
        type='Collect',
        keys=['img', 'proposals'],
        meta_keys=['scores', 'img_shape'],
        nested=True)
]

data = dict(
    videos_per_gpu=2,
    workers_per_gpu=2,
    val_dataloader=dict(videos_per_gpu=2),
    test_dataloader=dict(videos_per_gpu=2),
    train=dict(
        type=dataset_type,
        ann_file=ann_file_train,
        exclude_file=exclude_file_train,
        pipeline=train_pipeline,
        label_file=label_file,
        proposal_file=proposal_file_train,
        person_det_score_thr=0.9,
        num_classes=num_classes,
        custom_classes=custom_classes,
        data_prefix=data_root),
    val=dict(
        type=dataset_type,
        ann_file=ann_file_val,
        exclude_file=exclude_file_val,
        pipeline=val_pipeline,
        label_file=label_file,
        proposal_file=proposal_file_val,
        person_det_score_thr=0.9,
        num_classes=num_classes,
        custom_classes=custom_classes,
        data_prefix=data_root))
data['test'] = data['val']

optimizer = dict(type='SGD', lr=0.1125, momentum=0.9, weight_decay=0.00001)
# this lr is used for 8 gpus

optimizer_config = dict(grad_clip=dict(max_norm=40, norm_type=2))
# learning policy
gpu_ids=[0]
lr_config = dict(
    policy='step',
    step=[10, 15],
    warmup='linear',
    warmup_by_epoch=True,
    warmup_iters=5,
    warmup_ratio=0.05)
total_epochs = 100
checkpoint_config = dict(interval=20)
workflow = [('train', 1)]
evaluation = dict(interval=1, save_best='mAP@0.5IOU')
log_config = dict(
    interval=1, hooks=[
        dict(type='TextLoggerHook'),
    ])
dist_params = dict(backend='nccl')
log_level = 'INFO'
work_dir = ('./work_dirs/ava/'
            'slowfast_kinetics_pretrained_r50_4x16x1_20e_ava_rgb_custom')
load_from = ('https://download.openmmlab.com/mmaction/recognition/slowfast/'
             'slowfast_r50_4x16x1_256e_kinetics400_rgb/'
             'slowfast_r50_4x16x1_256e_kinetics400_rgb_20200704-bcde7ed7.pth')
resume_from = None
find_unused_parameters = False

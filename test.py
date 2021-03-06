import argparse
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
from modeling.build_model import Pose2Seg
from datasets.CocoDatasetInfo import CocoDatasetInfo, annToMask
from pycocotools import mask as maskUtils
# from pathlib import Path
def test(model, dataset='cocoVal', logger=print):    
    if dataset == 'OCHumanVal':
        ImageRoot = r'\\fs01\Algo\ML\Datasets\Pose2Seg\data\OCHuman\images'
        AnnoFile = r'\\fs01\Algo\ML\Datasets\Pose2Seg\data\OCHuman\annotations\ochuman_coco_format_val_range_0.00_1.00.json'
    elif dataset == 'OCHumanTest':
        ImageRoot = r'\\fs01\Algo\ML\Datasets\Pose2Seg\data\OCHuman\images'
        AnnoFile = r'\\fs01\Algo\ML\Datasets\Pose2Seg\data\OCHuman\annotations\ochuman_coco_format_test_range_0.00_1.00.json'
    elif dataset == 'cocoVal':
        ImageRoot = r'\\fs01\Algo\ML\Datasets\Pose2Seg\data\coco2017\val2017'
        AnnoFile = r'\\fs01\Algo\ML\Datasets\Pose2Seg\data\coco2017\annotations\person_keypoints_val2017_pose2seg.json'
    datainfos = CocoDatasetInfo(ImageRoot, AnnoFile, onlyperson=True, loadimg=True)
    
    model.eval()
    
    results_segm = []
    imgIds = []
    for i in tqdm(range(3,len(datainfos))):
        rawdata = datainfos[i]
        img = rawdata['data']
        image_id = rawdata['id']
        
        height, width = img.shape[0:2]
        gt_kpts = np.float32(rawdata['gt_keypoints']).transpose(0, 2, 1) # (N, 17, 3)
        gt_segms = rawdata['segms']
        gt_masks = np.array([annToMask(segm, height, width) for segm in gt_segms])
        output = model([img], [gt_kpts], [gt_masks])

        img = img[..., ::-1]
        # plt.switch_backend("TkAgg")
        # plt.imshow(gt_masks[0,...])
        # plt.show()

        # fig.savefig('C:\\Users\\erez\\Projects\\Pose2Seg\\demo.png', bbox_inches='tight')

        MASKS = np.zeros(output[0][0].shape)
        for id,mask in enumerate(output[0]):
            from skimage.color import label2rgb
            MASKS+=(id + 1) * mask
            maskencode = maskUtils.encode(np.asfortranarray(mask))
            maskencode['counts'] = maskencode['counts'].decode('ascii')
            results_segm.append({
                    "image_id": image_id,
                    "category_id": 1,
                    "score": 1.0,
                    "segmentation": maskencode
                })
        imgIds.append(image_id)

        image_label_overlay = label2rgb(MASKS, image=img, alpha=0.3, bg_label=0)
        plt.imshow(image_label_overlay)
        plt.show()
    
    def do_eval_coco(image_ids, coco, results, flag):
        from pycocotools.cocoeval import COCOeval
        assert flag in ['bbox', 'segm', 'keypoints']
        # Evaluate
        coco_results = coco.loadRes(results)
        cocoEval = COCOeval(coco, coco_results, flag)
        cocoEval.params.imgIds = image_ids
        cocoEval.params.catIds = [1]
        cocoEval.evaluate()
        cocoEval.accumulate()
        cocoEval.summarize() 
        return cocoEval
    
    cocoEval = do_eval_coco(imgIds, datainfos.COCO, results_segm, 'segm')
    logger('[POSE2SEG]          AP|.5|.75| S| M| L|    AR|.5|.75| S| M| L|')
    _str = '[segm_score] %s '%dataset
    for value in cocoEval.stats.tolist():
        _str += '%.3f '%value
    logger(_str)
    
if __name__=='__main__':
    parser = argparse.ArgumentParser(description="Pose2Seg Testing")
    parser.add_argument(
        "--weights",
        help="path to .pkl model weight",
        type=str,
    )
    parser.add_argument(
        "--coco",
        help="Do test on COCOPersons val set",
        action="store_true",
    )
    parser.add_argument(
        "--OCHuman",
        help="Do test on OCHuman val&test set",
        action="store_true",
    )
    
    args = parser.parse_args()
    
    print('===========> loading model <===========')
    model = Pose2Seg().cuda()
    model.init(args.weights)
            
    print('===========>   testing    <===========')
    if args.coco:
        test(model, dataset='cocoVal') 
    if args.OCHuman:
        test(model, dataset='OCHumanVal')
        test(model, dataset='OCHumanTest') 

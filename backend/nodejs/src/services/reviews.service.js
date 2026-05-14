import { parseJsonArray } from "../utils.js";
import { getUserById } from "../shared/dto/userDto.js";
import { withTransaction } from "../shared/db/withTransaction.js";
import * as reviewsRepository from "../repositories/reviews.repository.js";

export async function listReviewsForDestination(destinationId) {
  const rows = await reviewsRepository.listReviewsByDestinationId(destinationId);
  return rows.map((r) => ({
    id: r.id,
    userId: r.user_id,
    userName: r.user_name,
    userAvatar: r.user_avatar,
    destinationId: r.destination_id,
    rating: r.rating,
    comment: r.comment,
    images: parseJsonArray(r.images_json, null),
    createdAt: r.created_at
  }));
}

export async function createReview({ userId, destinationId, rating, comment, imageUrls }) {
  const destExists = await reviewsRepository.destinationExists(destinationId);
  if (!destExists) {
    return { ok: false, reason: "destination_not_found" };
  }

  const urls = Array.isArray(imageUrls) ? imageUrls : [];
  const imagesJson = urls.length > 0 ? JSON.stringify(urls) : null;

  const info = await withTransaction(async (conn) => {
    const insertInfo = await reviewsRepository.insertReview(
      {
        userId,
        destinationId,
        rating,
        comment,
        imagesJson
      },
      conn
    );

    const agg = await reviewsRepository.getReviewAggregateByDestinationId(destinationId, conn);
    await reviewsRepository.updateDestinationReviewAggregate(
      {
        destinationId,
        rating: Number(agg.avg ?? 0),
        reviewCount: Number(agg.cnt ?? 0)
      },
      conn
    );

    return insertInfo;
  });

  const user = await getUserById(userId);
  const review = {
    id: Number(info.lastInsertRowid),
    userId,
    userName: user.full_name,
    userAvatar: user.avatar,
    destinationId,
    rating,
    comment,
    images: urls.length > 0 ? urls : null,
    createdAt: new Date().toISOString()
  };

  return { ok: true, review };
}
